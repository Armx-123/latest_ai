import os
import json
import time
import requests
import feedparser
import re

# --- Configuration ---
API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# Using v1beta for widest 2026 model support
MODEL = "gemini-1.5-flash" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

def extract_json(text):
    try:
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except: return []

def run_pipeline():
    file_path = 'ai_models.json'
    
    # 1. LOAD & CLEAN DATA
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                raw = json.load(f)
                data = {"last_id": str(raw.get("last_id", "")), "categories": raw.get("categories", {})}
            except: data = {"last_id": "", "categories": {}}
    else:
        data = {"last_id": "", "categories": {}}

    # 2. CHECK RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    latest = feed.entries[0]
    v_id = latest.yt_videoid if hasattr(latest, 'yt_videoid') else None
    
    if not v_id or v_id == data["last_id"]:
        print("Everything up to date.")
        return

    print(f"Analyzing: {latest.title}")

    # 3. CONTEXTUAL PROMPT
    # We send the current categories to Gemini so it knows what it's replacing
    current_list = "\n".join([f"- {c}: {v['name']}" for c, v in data['categories'].items()])
    
    prompt = (
        f"Video: {latest.title}\nDescription: {latest.description}\n\n"
        f"CURRENT LEADERS:\n{current_list}\n\n"
        "TASK:\n"
        "1. Extract ONLY Open Source / Open Weight AI models (e.g. Llama, Mistral, Flux, etc.).\n"
        "2. STRICTLY IGNORE: Proprietary models (GPT, Claude), sponsor links, affiliate links, and social media.\n"
        "3. REPLACEMENT LOGIC: If a model in the video is a NEW 'best' or 'better variant' for a category, set 'is_better' to true.\n"
        "4. If this is just an explainer video with no specific models to track, return [].\n\n"
        "RETURN ONLY JSON: [{\"category\": \"...\", \"name\": \"...\", \"link\": \"...\", \"is_better\": bool, \"reason\": \"...\"}]"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}

    try:
        res = requests.post(API_URL, json=payload, timeout=60)
        if res.status_code != 200: return
        
        raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
        new_models = extract_json(raw_text)

        if not new_models:
            print("No relevant Open Source models found. Skipping update.")
            data["last_id"] = v_id # Still mark as processed so we don't check again
        else:
            for item in new_models:
                cat = item.get('category', 'Misc')
                # Replace if: New category OR is_better flag is true
                if cat not in data['categories'] or item.get('is_better'):
                    print(f"Updating {cat} to {item['name']}")
                    data['categories'][cat] = {
                        "name": item['name'],
                        "link": item['link'],
                        "reason": item['reason'],
                        "source": f"https://youtu.be/{v_id}"
                    }
            data["last_id"] = v_id

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_pipeline()
