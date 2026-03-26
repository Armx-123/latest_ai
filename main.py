import os
import json
import time
import requests
import feedparser
import re

# --- Configuration ---
# Ensure your GitHub Secret is named EXACTLY 'GEMINI_API_KEY'
API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def run_pipeline():
    # 1. LOAD LOCAL FILE (Strictly local to avoid GitHub Web Junk)
    file_path = 'ai_models.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                # Force clean-up: if junk keys exist, remove them
                data = {
                    "last_processed_video_id": data.get("last_processed_video_id", ""),
                    "categories": data.get("categories", {})
                }
            except:
                data = {"last_processed_video_id": "", "categories": {}}
    else:
        data = {"last_processed_video_id": "", "categories": {}}

    # 2. CHECK RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    
    latest_v = feed.entries[0]
    v_id = latest_v.yt_videoid if hasattr(latest_v, 'yt_videoid') else None
    
    if not v_id or v_id == data["last_processed_video_id"]:
        print("No new video. Skipping.")
        return

    print(f"Processing new video: {v_id}")

    # 3. ASK GEMINI (Strict JSON Enforcement)
    prompt = (
        f"Video Title: {latest_v.title}\n"
        f"Description: {latest_v.description}\n\n"
        "Instructions: Extract AI tools from this text. Identify the category. "
        "Return ONLY valid JSON in this format: "
        "[{\"category\": \"string\", \"name\": \"string\", \"link\": \"string\", \"is_best\": bool, \"reason\": \"string\"}]"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application_json"}
    }

    try:
        res = requests.post(API_URL, json=payload, timeout=30)
        res_json = res.json()
        ai_list = json.loads(res_json['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e:
        print(f"Gemini Error: {e}")
        return

    # 4. UPDATE LOGIC
    for item in ai_list:
        cat = item['category']
        # If it's a new category OR Gemini says it's the 'best' (replacement)
        if cat not in data['categories'] or item.get('is_best'):
            data['categories'][cat] = {
                "name": item['name'],
                "link": item['link'],
                "reason": item['reason'],
                "source_video": f"https://youtu.be/{v_id}"
            }

    # 5. SAVE CLEAN DATA
    data["last_processed_video_id"] = v_id
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print("Successfully updated ai_models.json")

if __name__ == "__main__":
    run_pipeline()
