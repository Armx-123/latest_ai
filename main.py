import os
import json
import feedparser
from google.genai import Client  # Direct import to avoid namespace errors
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

# --- Configuration ---
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# The client automatically picks up GEMINI_API_KEY from environment
client = Client() 

def analyze_with_gemini(title, description, transcript):
    prompt = f"""
    Analyze this AI news data. Title: {title}. Description: {description}. Transcript: {transcript}.
    Identify AI tools. Return a JSON list: 
    [{{"category": "...", "name": "...", "link": "...", "is_replacement": bool, "reasoning": "..."}}]
    """
    
    # Modern 2026 Call Structure
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        )
    )
    # The new SDK provides the text attribute directly
    return json.loads(response.text)

def run_pipeline():
    if not os.path.exists('ai_models.json'):
        data = {"last_processed_video_id": "", "categories": {}}
    else:
        with open('ai_models.json', 'r') as f:
            data = json.load(f)

    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    
    latest_video = feed.entries[0]
    v_id = latest_video.yt_videoid
    
    if v_id == data.get('last_processed_video_id'):
        print("Everything is up to date.")
        return

    print(f"Analyzing: {latest_video.title}")
    
    # Transcript Logic
    try:
        lines = YouTubeTranscriptApi.get_transcript(v_id)
        transcript = " ".join([line['text'] for line in lines])
    except:
        transcript = "No transcript."

    analysis_results = analyze_with_gemini(latest_video.title, latest_video.description, transcript)

    for item in analysis_results:
        cat = item['category']
        if cat not in data['categories'] or item.get('is_replacement'):
            data['categories'][cat] = {
                "name": item['name'],
                "link": item['link'],
                "video_ref": f"https://youtu.be/{v_id}",
                "reasoning": item['reasoning']
            }

    data['last_processed_video_id'] = v_id
    with open('ai_models.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    run_pipeline()
