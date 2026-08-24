#!/usr/bin/env python3
"""Ingest EgoDex (human egocentric) from yixuan-tan/EgoDex-LeRobot-v3.0.
Target: 150 entries, 5-10s clips, hand visible in init_frame.
"""
import os, sys, json, re, time, random, subprocess, tempfile, shutil
from pathlib import Path
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"
DATA = Path(os.environ.get("EWJ_DATA_ROOT", "./data"))  # set EWJ_DATA_ROOT to your data/ root
TARGET_TOTAL = 150
DS_NAME = "egodex_human"  # new dataset folder
random.seed(42)

REPO = "yixuan-tan/EgoDex-LeRobot-v3.0"
LOCAL_CACHE = "/tmp/egodex_cache"

HAND_TMPL = """Is at least one HUMAN HAND clearly visible in this image (egocentric first-person view)? STRICT: needs recognizable fingers/palm; just a wrist or sleeve doesn't count. Reply EXACTLY: {{"hand_visible": true|false, "evidence": "<≤15 words>"}}"""

REFINE_TMPL = """init_frame of a human egocentric manipulation task. Original prompt: "{prompt}"

Write a refined ONE-LINE imperative task instruction grounded in this frame:
1. Imperative form, start with verb
2. Name SPECIFIC visible objects (color/shape) and target locations
3. Use "hand" or "left/right hand" (NOT gripper — this is human)
4. NO meta-commentary, NO scene words ("in a kitchen") unless verifiable
5. Real task command not description

Reply EXACTLY: {{"refined": "<one-line imperative>"}}"""

client = genai.Client(api_key=API_KEY)

def gemini(prompt, img, max_retries=4):
    parts = [types.Part(inline_data=types.Blob(mime_type="image/png", data=img)),
             types.Part(text=prompt)]
    cfg = types.GenerateContentConfig(response_mime_type="application/json")
    backoff = 1.0
    for _ in range(max_retries):
        try:
            resp = client.models.generate_content(model=MODEL,
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

def slice_video(src, from_ts, to_ts, out):
    duration = to_ts - from_ts
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(from_ts),'-i',str(src),'-t',str(duration),
                    '-c:v','libx264','-preset','veryfast','-crf','22','-an',str(out)], capture_output=True, timeout=60)
    return out.exists()

def extract_frame(video, t, out):
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1',str(out)], capture_output=True, timeout=20)
    return out.exists() and out.stat().st_size > 1000

def main():
    if not API_KEY: print("no key"); sys.exit(1)
    api = HfApi()
    # List all task names
    files = api.list_repo_files(REPO, repo_type="dataset")
    tasks = sorted(set(f.split('/')[1] for f in files if f.startswith('test/')))
    print(f"available tasks: {len(tasks)}")
    random.shuffle(tasks)

    DEST_BASE = DATA/DS_NAME
    DEST_BASE.mkdir(parents=True, exist_ok=True)
    (DEST_BASE/"gt_data").mkdir(parents=True, exist_ok=True)

    summary = []
    entry_idx = 1

    for task in tasks:
        if len(summary) >= TARGET_TOTAL: break
        try:
            # Download meta
            ep_path = hf_hub_download(REPO, f"test/{task}/meta/episodes/chunk-000/file-000.parquet",
                                       repo_type="dataset", local_dir=LOCAL_CACHE)
            tasks_path = hf_hub_download(REPO, f"test/{task}/meta/tasks.parquet",
                                          repo_type="dataset", local_dir=LOCAL_CACHE)
            ep_df = pq.read_table(ep_path).to_pandas()
            tasks_df = pq.read_table(tasks_path).to_pandas()
            task_texts = list(tasks_df.index)  # task texts are the index
        except Exception as e:
            print(f"  SKIP {task}: meta err {e}")
            continue

        # Filter eps to 5-10s
        vid_key = None
        for c in ep_df.columns:
            if "from_timestamp" in c and "observation.images.camera" in c:
                vid_key = c.replace("/from_timestamp", "")
                break
        if not vid_key:
            print(f"  SKIP {task}: no video timestamp col")
            continue

        good_eps = []
        for _, row in ep_df.iterrows():
            dur = float(row[f"{vid_key}/to_timestamp"]) - float(row[f"{vid_key}/from_timestamp"])
            if 5.0 <= dur <= 10.0:
                good_eps.append(row)
        random.shuffle(good_eps)
        # Cap per task to 3 for diversity
        good_eps = good_eps[:3]
        print(f"  {task}: {len(good_eps)} eps in 5-10s range (cap 3)", flush=True)

        for row in good_eps:
            if len(summary) >= TARGET_TOTAL: break
            from_ts = float(row[f"{vid_key}/from_timestamp"])
            to_ts = float(row[f"{vid_key}/to_timestamp"])
            ep_idx = int(row['episode_index'])
            # row['tasks'] is a list of text strings directly
            tasks_list = row['tasks']
            orig_prompt = str(tasks_list[0]) if hasattr(tasks_list, '__getitem__') and len(tasks_list) > 0 else "manipulate items"
            # Strip "{task}: " prefix if present
            if orig_prompt.startswith(f"{task}: "):
                orig_prompt = orig_prompt[len(task)+2:]

            chunk_idx = int(row[f"{vid_key}/chunk_index"])
            file_idx = int(row[f"{vid_key}/file_index"])
            video_rel = f"test/{task}/videos/observation.images.camera/chunk-{chunk_idx:03d}/file-{file_idx:03d}.mp4"
            try:
                chunk_path = hf_hub_download(REPO, video_rel, repo_type="dataset", local_dir=LOCAL_CACHE)
            except Exception as e:
                print(f"    DL err {video_rel}: {str(e)[:80]}")
                continue

            # Prep dest
            new_task = f"task_{entry_idx:04d}"
            dest_dir = DEST_BASE/"gt_data"/new_task/"episode_0001"
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir/"prompt").mkdir(parents=True, exist_ok=True)
            dest_video = dest_dir/"video.mp4"
            # Slice
            if not slice_video(chunk_path, from_ts, to_ts, dest_video):
                shutil.rmtree(dest_dir.parent)
                continue
            # Extract init_frame
            init_png = dest_dir/"prompt/init_frame.png"
            if not extract_frame(dest_video, 0, init_png):
                shutil.rmtree(dest_dir.parent)
                continue
            # Hand check
            with open(init_png, 'rb') as f: img = f.read()
            h = gemini(HAND_TMPL, img)
            if not h or not h.get('hand_visible'):
                # Try a later frame (0.5s, 1.0s)
                found = False
                with tempfile.TemporaryDirectory() as tmp:
                    for t_off in [0.3, 0.7, 1.2, 1.8]:
                        tmp_png = Path(tmp)/f"p{t_off}.png"
                        if not extract_frame(dest_video, t_off, tmp_png): continue
                        with open(tmp_png, 'rb') as f: img = f.read()
                        h2 = gemini(HAND_TMPL, img)
                        if h2 and h2.get('hand_visible'):
                            shutil.copy2(tmp_png, init_png)
                            found = True
                            break
                if not found:
                    shutil.rmtree(dest_dir.parent)
                    print(f"    SKIP {new_task}: no hand in any frame")
                    continue
            # Refine prompt
            with open(init_png, 'rb') as f: img = f.read()
            r = gemini(REFINE_TMPL.format(prompt=orig_prompt), img)
            if not r or not r.get('refined'):
                shutil.rmtree(dest_dir.parent)
                continue
            new_refined = r['refined'].strip()
            (dest_dir/"prompt/prompt.txt").write_text(new_refined)
            (dest_dir/"prompt/prompt_refined.txt").write_text(new_refined)
            # Duration
            dur = ffprobe_duration(dest_video) or (to_ts - from_ts)
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
    print(f"\nDONE: {len(summary)} egodex_human entries ingested")

if __name__ == "__main__":
    main()
