import os
import json
import time
import requests
import feedparser
import re

# --- Configuration ---
API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# We'll use v1 (stable) and gemini-1.5-flash for maximum compatibility
import os

# Option A: Current Stable (Recommended for 2026)
GEMINI_MODEL = "gemini-2.5-flash" 

# Option B: Always the Latest (Currently points to Gemini 3 Flash Preview)
# GEMINI_MODEL = "gemini-flash-latest"

# USE v1beta for maximum model support
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

def extract_json_from_text(text):
    """
    Safely extracts a JSON array from a text string, 
    even if the model includes conversational filler.
    """
    try:
        # Look for content between [ and ]
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        # Fallback: try to parse the whole string
        return json.loads(text)
    except Exception:
        print(f"Failed to parse JSON from response: {text[:100]}...")
        return []

def run_pipeline():
    file_path = 'ai_models.json'
    
    # 1. Load and Sanitize Local Data
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                raw = json.load(f)
                data = {
                    "last_processed_video_id": str(raw.get("last_processed_video_id", "")),
                    "categories": raw.get("categories", {})
                }
            except: data = {"last_processed_video_id": "", "categories": {}}
    else:
        data = {"last_processed_video_id": "", "categories": {}}

    # 2. Check RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    
    latest_v = feed.entries[0]
    v_id = latest_v.yt_videoid if hasattr(latest_v, 'yt_videoid') else None
    
    if not v_id or v_id == data["last_processed_video_id"]:
        print(f"Video {v_id} already handled.")
        return

    print(f"Analyzing: {latest_v.title}")

    # 3. Request (WITHOUT responseMimeType to avoid 400 error)
    prompt = (
        f"You are a tech curator. Analyze the following video data.\n"
        f"Title: {latest_v.title}\n"
        f"Description: {latest_v.description}\n\n"
        "Return a JSON list of AI tools mentioned. If a tool is a major new 'best' in its class, set is_better to true.\n"
        "Format: [{\"category\": \"string\", \"name\": \"string\", \"link\": \"string\", \"is_better\": bool, \"reason\": \"string\"}]\n"
        "Return ONLY the JSON array, no other text."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2 # Lower temperature = more consistent JSON
        }
    }

    try:
        res = requests.post(API_URL, json=payload, timeout=60)
        if res.status_code != 200:
            print(f"API Error: {res.status_code} - {res.text}")
            return

        response_data = res.json()
        raw_text = response_data['candidates'][0]['content']['parts'][0]['text']
        ai_list = extract_json_from_text(raw_text)

        if not ai_list:
            print("No AI models found in this video.")
        
        for item in ai_list:
            cat = item.get('category', 'Misc')
            if cat not in data['categories'] or item.get('is_better'):
                data['categories'][cat] = {
                    "name": item['name'],
                    "link": item['link'],
                    "reason": item['reason'],
                    "updated_at": time.strftime("%Y-%m-%d"),
                    "video": f"https://youtu.be/{v_id}"
                }

        data["last_processed_video_id"] = v_id
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        print("Success: ai_models.json updated.")

    except Exception as e:
        print(f"Error in pipeline: {e}")

if __name__ == "__main__":
    run_pipeline()
