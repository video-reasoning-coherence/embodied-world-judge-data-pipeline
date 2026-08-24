#!/usr/bin/env python3
"""Ingest egoscaler-v2 (Biscue5/egoscaler-v2): 1-4s human-hand egocentric clips.
Target: 100 entries, sampled across the 45K episodes for diversity.
"""
import os, sys, json, re, time, random, subprocess, tempfile, shutil
from pathlib import Path
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATA = Path(os.environ.get("EWJ_DATA_ROOT", "./data"))  # set EWJ_DATA_ROOT to your data/ root
TARGET_TOTAL = 100
DS_NAME = "egoscaler_human"
random.seed(42)

REPO = "Biscue5/egoscaler-v2"
LOCAL_CACHE = os.environ.get("HF_HOME", "/tmp/egoscaler_cache")

HAND_TMPL = """Is at least one HUMAN HAND clearly visible in this egocentric image? STRICT: needs recognizable fingers/palm. Reply: {{"hand_visible": true|false, "evidence": "<≤15w>"}}"""

REFINE_TMPL = """init_frame of a human egocentric manipulation task. Original prompt: "{prompt}"

Write a refined ONE-LINE imperative task instruction grounded in this frame:
1. Imperative form, start with verb
2. Name SPECIFIC visible objects (color/shape) and target locations
3. Use "hand" or "left/right hand" (NOT gripper)
4. NO meta-commentary, NO scene words unless verifiable

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

    # Load episodes meta
    eps_path = hf_hub_download(REPO, "meta/episodes.jsonl", repo_type="dataset", local_dir=LOCAL_CACHE)
    info_path = hf_hub_download(REPO, "meta/info.json", repo_type="dataset", local_dir=LOCAL_CACHE)
    tasks_path = hf_hub_download(REPO, "meta/tasks.jsonl", repo_type="dataset", local_dir=LOCAL_CACHE)
    info = json.load(open(info_path))
    eps = [json.loads(l) for l in open(eps_path)]
    tasks = {int(json.loads(l)['task_index']): json.loads(l)['task'] for l in open(tasks_path)}
    print(f"loaded {len(eps)} eps, {len(tasks)} task texts, fps={info.get('fps')}", flush=True)

    # Sample 100 eps with diverse task_index
    random.shuffle(eps)
    # Get unique task_indexes for variety
    chosen = []
    seen_tasks = {}  # task_idx → count
    for ep in eps:
        ep_idx = ep['episode_index']
        ti = ep.get('tasks')
        if not ti: continue
        # tasks is a list of task texts in this dataset (not indices)
        task_text = str(ti[0]) if len(ti) > 0 else ""
        # Limit per task_text to 2 for diversity
        if seen_tasks.get(task_text, 0) >= 2: continue
        chosen.append((ep_idx, task_text, ep))
        seen_tasks[task_text] = seen_tasks.get(task_text, 0) + 1
        if len(chosen) >= TARGET_TOTAL * 2: break  # Get more candidates for skip-margin

    print(f"selected {len(chosen)} candidates", flush=True)
    video_path_template = info['video_path']  # videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4
    chunks_size = info.get('chunks_size', 1000)
    summary = []
    entry_idx = 1

    for ep_idx, orig_prompt, ep_meta in chosen:
        if len(summary) >= TARGET_TOTAL: break
        chunk_idx = ep_idx // chunks_size
        vid_rel = video_path_template.format(
            episode_chunk=chunk_idx,
            video_key="observation.images.cam_high",
            episode_index=ep_idx)
        try:
            src_vid = hf_hub_download(REPO, vid_rel, repo_type="dataset", local_dir=LOCAL_CACHE)
        except Exception as e:
            continue

        new_task = f"task_{entry_idx:04d}"
        dest_dir = DEST_BASE/"gt_data"/new_task/"episode_0001"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir/"prompt").mkdir(parents=True, exist_ok=True)
        dest_video = dest_dir/"video.mp4"

        # Re-encode to H.264 (egoscaler may use AV1)
        tmp_h264 = dest_dir/"tmp.mp4"
        subprocess.run(['ffmpeg','-v','error','-y','-i',src_vid,'-c:v','libx264','-crf','22','-preset','veryfast','-an',str(tmp_h264)],
                       capture_output=True, timeout=60)
        if tmp_h264.exists():
            tmp_h264.rename(dest_video)
        else:
            shutil.copy2(src_vid, dest_video)

        init_png = dest_dir/"prompt/init_frame.png"
        if not extract_frame(dest_video, 0, init_png):
            shutil.rmtree(dest_dir.parent)
            continue
        # Hand check
        img = init_png.read_bytes()
        h = gemini(HAND_TMPL, img)
        if not h or not h.get('hand_visible'):
            # Try later frames
            found = False
            with tempfile.TemporaryDirectory() as tmp:
                for t_off in [0.3, 0.5, 0.8, 1.2]:
                    tmp_png = Path(tmp)/f"p{t_off}.png"
                    if not extract_frame(dest_video, t_off, tmp_png): continue
                    img = tmp_png.read_bytes()
                    h2 = gemini(HAND_TMPL, img)
                    if h2 and h2.get('hand_visible'):
                        shutil.copy2(tmp_png, init_png)
                        found = True; break
            if not found:
                shutil.rmtree(dest_dir.parent)
                continue
        # Refine
        img = init_png.read_bytes()
        r = gemini(REFINE_TMPL.format(prompt=orig_prompt), img)
        if not r or not r.get('refined'):
            shutil.rmtree(dest_dir.parent)
            continue
        new_refined = r['refined'].strip()
        (dest_dir/"prompt/prompt.txt").write_text(new_refined)
        (dest_dir/"prompt/prompt_refined.txt").write_text(new_refined)
        dur = ffprobe_duration(dest_video) or 2.0
        entry = {
            'gt_path': f"data/{DS_NAME}/gt_data/{new_task}/episode_0001/video.mp4",
            'image': f"data/{DS_NAME}/gt_data/{new_task}/episode_0001/prompt/init_frame.png",
            'prompt': [new_refined],
            'task_name': new_task,
            'episode_name': "episode_0001",
            'duration': round(dur, 3),
        }
        summary.append(entry)
        entry_idx += 1
        if entry_idx % 10 == 0:
            json.dump(summary, open(DEST_BASE/"summary.json", "w"), indent=2, ensure_ascii=False)
            print(f"  TOTAL {len(summary)}/{TARGET_TOTAL}", flush=True)

    json.dump(summary, open(DEST_BASE/"summary.json", "w"), indent=2, ensure_ascii=False)
    print(f"\nDONE: {len(summary)} egoscaler entries")

if __name__ == "__main__":
    main()
