import os
import re
import time
import json
import requests
import feedparser

# --- Configuration ---
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
API_KEY = os.getenv("GEMINI_API_KEY")
# Using 1.5-flash for stability and speed in automation
GEMINI_MODEL = "gemini-1.5-flash" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

def extract_video_id(url):
    reg_exp = r"^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*"
    match = re.match(reg_exp, url)
    if match and len(match.group(7)) == 11:
        return match.group(7)
    return None

def analyze_video_with_backoff(video_url, description):
    """
    Uses your requests logic to ask Gemini to analyze the AI models.
    """
    system_prompt = (
        "You are an AI market analyst. Analyze the provided video content and description. "
        "Extract a list of AI models mentioned. Categorize them. "
        "Identify if any are claimed to be 'the new best' or a replacement for existing tech. "
        "Return ONLY a JSON array of objects: "
        "[{\"category\": \"...\", \"name\": \"...\", \"link\": \"...\", \"is_replacement\": bool, \"reasoning\": \"...\"}]"
    )
    
    # We pass the description directly to ensure the AI has the source links
    user_prompt = f"Analyze this video: {video_url}\nDescription links: {description}"

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application_json"}
    }

    max_retries = 5
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                API_URL,
                headers={"Content-Type": "application/json"},
                json=payload
            )

            if response.status_code == 200:
                result = response.json()
                try:
                    raw_text = result['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(raw_text)
                except (KeyError, IndexError, json.JSONDecodeError):
                    return []
            
            if response.status_code in [429, 500, 502, 503, 504]:
                time.sleep(2 ** attempt)
                continue
            
            break
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
            
    return []

def run_pipeline():
    # 1. Load existing JSON
    if os.path.exists('ai_models.json'):
        with open('ai_models.json', 'r') as f:
            data = json.load(f)
    else:
        data = {"last_processed_video_id": "", "categories": {}}

    # 2. Check for new video
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        return
    
    latest_video = feed.entries[0]
    v_id = extract_video_id(latest_video.link)
    
    if v_id == data.get('last_processed_video_id'):
        print("No new updates found.")
        return

    print(f"New video detected: {latest_video.title}")

    # 3. Analyze
    analysis_results = analyze_video_with_backoff(latest_video.link, latest_video.description)

    # 4. Update Categories (Replacement Logic)
    for item in analysis_results:
        cat = item['category']
        # Replace if: New category OR explicitly marked as a better replacement
        if cat not in data['categories'] or item.get('is_replacement'):
            print(f"Updating {cat} -> {item['name']}")
            data['categories'][cat] = {
                "name": item['name'],
                "link": item['link'],
                "updated_at": time.strftime("%Y-%m-%d"),
                "video_source": latest_video.link,
                "reasoning": item['reasoning']
            }

    # 5. Save State
    data['last_processed_video_id'] = v_id
    with open('ai_models.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    run_pipeline()
