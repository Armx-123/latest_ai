import os
import json
import time
import requests
import feedparser
import re

# --- Configuration ---
API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# Using v1beta for widest 2026 support
MODEL = "gemini-2.5-flash" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

def extract_json(text):
    try:
        # Matches content between the first [ and the last ]
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except: return []

def run_pipeline():
    file_path = 'ai_models.json'
    
    # 1. LOAD DATA
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                raw = json.load(f)
                data = {
                    "last_id": str(raw.get("last_id", "")), 
                    "categories": raw.get("categories", {}),
                    "last_updated_unix": raw.get("last_updated_unix", 0)
                }
            except: data = {"last_id": "", "categories": {}, "last_updated_unix": 0}
    else:
        data = {"last_id": "", "categories": {}, "last_updated_unix": 0}

    # 2. CHECK RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    latest = feed.entries[0]
    
    # Reliable ID extraction
    v_id_match = re.search(r"v=([a-zA-Z0-9_-]{11})", latest.link)
    v_id = v_id_match.group(1) if v_id_match else None
    
    if not v_id or v_id == data["last_id"]:
        print(f"Skipping: Video {v_id} already processed.")
        return

    print(f"Analyzing: {latest.title} ({v_id})")

    # 3. CONTEXTUAL PROMPT
    current_models = ", ".join([v['name'] for v in data['categories'].values()])
    
    prompt = (
        f"Video Title: {latest.title}\nDescription: {latest.description}\n\n"
        f"We currently track these models: {current_models}\n\n"
        "Instructions:\n"
        "1. Extract ONLY Open Source AI models mentioned. Ignore proprietary ones (GPT-4, Claude).\n"
        "2. Strictly ignore sponsor links (VPNs, Squarespace, etc.) and social media links.\n"
        "3. If a mentioned model is a new 'best' or 'latest version' for a category, set 'is_better' to true.\n"
        "4. If no specific Open Source models are discussed, return an empty list [].\n"
        "Format: [{\"category\": \"...\", \"name\": \"...\", \"link\": \"...\", \"is_better\": bool, \"reason\": \"...\"}]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}

    # Pre-emptively update ID to mark it as seen
    data["last_id"] = v_id

    try:
        res = requests.post(API_URL, json=payload, timeout=60)
        if res.status_code == 200:
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            new_models = extract_json(raw_text)

            if new_models:
                for item in new_models:
                    cat = item.get('category', 'General')
                    if cat not in data['categories'] or item.get('is_better'):
                        print(f"Updating {cat} -> {item['name']}")
                        data['categories'][cat] = {
                            "name": item['name'],
                            "link": item['link'],
                            "reason": item['reason'],
                            "source": f"https://youtu.be/{v_id}",
                            "date": time.strftime("%Y-%m-%d"),
                            "updated_at_unix": int(time.time())
                        }
            else:
                print("No new open-source models found in this video.")
        else:
            print(f"API Error: {res.status_code}. ID tracked to prevent retry loop.")

    except Exception as e:
        print(f"Pipeline error: {e}")

    # 4. UPDATE GLOBAL TIMESTAMP & SAVE
    # This ensures Git always has a change to commit when a new video is found
    data["last_updated_unix"] = int(time.time())
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"State saved to ai_models.json (Timestamp: {data['last_updated_unix']})")

if __name__ == "__main__":
    run_pipeline()
