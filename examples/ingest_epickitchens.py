#!/usr/bin/env python3
"""Ingest EpicKitchens-100 clips (lightly-ai/epic-kitchens-100-clips):
50 entries, 5-10s clips, kitchen egocentric human hand.
"""
import os, sys, json, re, time, random, subprocess, tempfile, shutil
from pathlib import Path
import pandas as pd
from huggingface_hub import hf_hub_download
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATA = Path(os.environ.get("EWJ_DATA_ROOT", "./data"))  # set EWJ_DATA_ROOT to your data/ root
TARGET_TOTAL = 60
DS_NAME = "epickitchens_human"
random.seed(42)

REPO = "lightly-ai/epic-kitchens-100-clips"
LOCAL_CACHE = os.environ.get("HF_HOME", "/tmp/ek_cache")

HAND_TMPL = """Is at least one HUMAN HAND clearly visible in this egocentric image? Reply: {{"hand_visible": true|false, "evidence": "<≤15w>"}}"""

REFINE_TMPL = """init_frame of a human egocentric kitchen task. Original prompt: "{prompt}"

Write a refined ONE-LINE imperative task instruction grounded in this frame:
1. Imperative form, start with verb
2. Name SPECIFIC visible objects (color/material) and target locations
3. Use "hand" or "left/right hand" (NOT gripper)
4. NO meta-commentary

Reply: {{"refined": "<one-line>"}}"""

client = genai.Client(api_key=API_KEY)

def gemini(prompt, img, max_retries=4):
    parts = [types.Part(inline_data=types.Blob(mime_type="image/png", data=img)),
             types.Part(text=prompt)]
    cfg = types.GenerateContentConfig(response_mime_type="application/json")
    backoff = 1.0
    for _ in range(max_retries):
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash",
                contents=[types.Content(role="user", parts=parts)], config=cfg)
            return json.loads((resp.text or "").strip())
        except Exception as ex:
            if any(s in str(ex) for s in ("503","429","UNAVAILABLE","RESOURCE_EXHAUSTED")):
                time.sleep(backoff); backoff *= 2; continue
            return None
    return None

def ffprobe_duration(p):
    try:
        return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
                                                '-of','default=noprint_wrappers=1:nokey=1', str(p)], text=True, timeout=10).strip())
    except: return None

def extract_frame(video, t, out):
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1',str(out)], capture_output=True, timeout=20)
    return out.exists() and out.stat().st_size > 1000

def main():
    if not API_KEY: print("no key"); sys.exit(1)
    DEST_BASE = DATA/DS_NAME
    DEST_BASE.mkdir(parents=True, exist_ok=True)
    (DEST_BASE/"gt_data").mkdir(parents=True, exist_ok=True)

    # Build list of available mp4 files (only some participants are bundled)
    from huggingface_hub import HfApi
    api = HfApi()
    all_files = api.list_repo_files(REPO, repo_type="dataset")
    avail = set()
    for f in all_files:
        if f.startswith('clips/') and f.endswith('.mp4'):
            narr_id = f.split('/')[-1].replace('.mp4', '')
            avail.add(narr_id)
    print(f"available narration clips: {len(avail)}", flush=True)

    # Load annotations - both train and validation, combine for max coverage
    df_list = []
    for csv_name in ['EPIC_100_train.csv', 'EPIC_100_validation.csv']:
        csv_path = hf_hub_download(REPO, f"epic-kitchens-100-annotations/{csv_name}",
                                    repo_type="dataset", local_dir=LOCAL_CACHE)
        df_list.append(pd.read_csv(csv_path))
    df = pd.concat(df_list, ignore_index=True)
    # Filter to those whose clip exists
    df = df[df['narration_id'].isin(avail)].copy()
    print(f"narrations with available clips: {len(df)}", flush=True)
    def to_sec(t):
        h, m, s = t.split(':')
        return int(h)*3600 + int(m)*60 + float(s)
    df['duration'] = df.apply(lambda r: to_sec(r['stop_timestamp']) - to_sec(r['start_timestamp']), axis=1)
    # Filter 5-10s
    df5_10 = df[df['duration'].between(5, 10)].copy()
    print(f"5-10s narrations: {len(df5_10)}", flush=True)

    # Sample for diversity: avoid same verb+noun repeats, mix participants
    df5_10['key'] = df5_10['verb'] + '_' + df5_10['noun']
    samples = []
    seen_keys = set()
    seen_participants = {}
    for _, row in df5_10.sample(frac=1, random_state=42).iterrows():
        k = row['key']
        p = row['participant_id']
        if k in seen_keys: continue
        if seen_participants.get(p, 0) >= 4: continue
        samples.append(row)
        seen_keys.add(k)
        seen_participants[p] = seen_participants.get(p, 0) + 1
        if len(samples) >= TARGET_TOTAL * 2: break
    print(f"diverse samples: {len(samples)}", flush=True)

    summary = []
    entry_idx = 1
    for row in samples:
        if len(summary) >= TARGET_TOTAL: break
        narr_id = row['narration_id']
        pid = row['participant_id']
        prompt_orig = row['narration']
        clip_rel = f"clips/{pid}/{narr_id}.mp4"
        try:
            src_vid = hf_hub_download(REPO, clip_rel, repo_type="dataset", local_dir=LOCAL_CACHE)
        except Exception as e:
            print(f"  DL err {narr_id}: {str(e)[:80]}")
            continue

        new_task = f"task_{entry_idx:04d}"
        dest_dir = DEST_BASE/"gt_data"/new_task/"episode_0001"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir/"prompt").mkdir(parents=True, exist_ok=True)
        dest_video = dest_dir/"video.mp4"
        shutil.copy2(src_vid, dest_video)

        init_png = dest_dir/"prompt/init_frame.png"
        if not extract_frame(dest_video, 0, init_png):
            shutil.rmtree(dest_dir.parent); continue
        img = init_png.read_bytes()
        h = gemini(HAND_TMPL, img)
        if not h or not h.get('hand_visible'):
            # Try later frames
            found = False
            with tempfile.TemporaryDirectory() as tmp:
                for t_off in [0.3, 0.7, 1.5, 2.5]:
                    tmp_png = Path(tmp)/f"p{t_off}.png"
                    if not extract_frame(dest_video, t_off, tmp_png): continue
                    img = tmp_png.read_bytes()
                    h2 = gemini(HAND_TMPL, img)
                    if h2 and h2.get('hand_visible'):
                        shutil.copy2(tmp_png, init_png)
                        found = True; break
            if not found:
                shutil.rmtree(dest_dir.parent); continue
        img = init_png.read_bytes()
        r = gemini(REFINE_TMPL.format(prompt=prompt_orig), img)
        if not r or not r.get('refined'):
            shutil.rmtree(dest_dir.parent); continue
        new_refined = r['refined'].strip()
        (dest_dir/"prompt/prompt.txt").write_text(new_refined)
        (dest_dir/"prompt/prompt_refined.txt").write_text(new_refined)
        dur = ffprobe_duration(dest_video) or row['duration']
        summary.append({
            'gt_path': f"data/{DS_NAME}/gt_data/{new_task}/episode_0001/video.mp4",
            'image': f"data/{DS_NAME}/gt_data/{new_task}/episode_0001/prompt/init_frame.png",
            'prompt': [new_refined],
            'task_name': new_task,
            'episode_name': "episode_0001",
            'duration': round(dur, 3),
        })
        entry_idx += 1
        if entry_idx % 10 == 0:
            json.dump(summary, open(DEST_BASE/"summary.json", "w"), indent=2, ensure_ascii=False)
            print(f"  TOTAL {len(summary)}/{TARGET_TOTAL}", flush=True)

    json.dump(summary, open(DEST_BASE/"summary.json", "w"), indent=2, ensure_ascii=False)
    print(f"\nDONE: {len(summary)} EpicKitchens entries")

if __name__ == "__main__":
    main()
