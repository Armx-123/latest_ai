import os
import json
import time
import requests
import feedparser
import re

# --- Configuration ---
# Make sure your GitHub Secret is named EXACTLY 'GEMINI_API_KEY'
API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# Using 2.0-flash (the 2026 stable workhorse)
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def run_pipeline():
    file_path = 'ai_models.json'
    
    # 1. LOAD & CLEAN LOCAL FILE
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                raw_data = json.load(f)
                # This line strips out any GitHub 'junk' metadata if it exists
                data = {
                    "last_processed_video_id": str(raw_data.get("last_processed_video_id", "")),
                    "categories": raw_data.get("categories", {})
                }
            except Exception:
                data = {"last_processed_video_id": "", "categories": {}}
    else:
        data = {"last_processed_video_id": "", "categories": {}}

    # 2. CHECK YOUTUBE RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("RSS Feed empty.")
        return
    
    latest_v = feed.entries[0]
    # Extract ID from the link (more reliable than yt_videoid)
    v_id_match = re.search(r"v=([a-zA-Z0-9_-]{11})", latest_v.link)
    v_id = v_id_match.group(1) if v_id_match else None
    
    if not v_id or v_id == data["last_processed_video_id"]:
        print(f"Skipping: {v_id} is already processed.")
        return

    print(f"Analyzing new video: {v_id} ({latest_v.title})")

    # 3. CALL GEMINI WITH ERROR LOGGING
    prompt = (
        f"Video Title: {latest_v.title}\n"
        f"Description: {latest_v.description}\n\n"
        "Extract AI models mentioned. Return ONLY a JSON list of objects: "
        "[{\"category\": \"string\", \"name\": \"string\", \"link\": \"string\", \"is_better\": bool, \"reason\": \"string\"}]"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application_json",
            "temperature": 0.1
        }
    }

    try:
        res = requests.post(API_URL, json=payload, timeout=60)
        
        if res.status_code != 200:
            print(f"API Error {res.status_code}: {res.text}")
            return

        res_json = res.json()
        
        # Check if 'candidates' exists (Safety/Refusal Check)
        if 'candidates' not in res_json:
            print(f"No candidates returned. Potential safety block. Full Response: {res_json}")
            return
            
        raw_ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
        ai_list = json.loads(raw_ai_text)
        
    except Exception as e:
        print(f"Pipeline crashed: {str(e)}")
        return

    # 4. UPDATE DATABASE
    for item in ai_list:
        cat = item.get('category', 'General AI')
        # Update if it's a new category or flagged as 'better'
        if cat not in data['categories'] or item.get('is_better'):
            print(f"Updating [{cat}] with {item['name']}")
            data['categories'][cat] = {
                "name": item['name'],
                "link": item['link'],
                "reason": item['reason'],
                "updated_at": time.strftime("%Y-%m-%d"),
                "source": f"https://youtu.be/{v_id}"
            }

    # 5. SAVE
    data["last_processed_video_id"] = v_id
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print("Done! ai_models.json updated.")

if __name__ == "__main__":
    run_pipeline()
