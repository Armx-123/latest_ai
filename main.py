import os
import json
import feedparser
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

# --- Configuration ---
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
# The new SDK automatically looks for GEMINI_API_KEY in your env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_transcript(video_id):
    try:
        lines = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([line['text'] for line in lines])
    except Exception:
        return "No transcript available."

def analyze_with_gemini(title, description, transcript):
    prompt = f"""
    Analyze this AI news data:
    Title: {title}
    Description: {description}
    Transcript: {transcript}

    Task: Identify AI tools mentioned. Determine if they are 'best in class' or replacements for existing tech.
    Return a JSON list of objects:
    [
      {{
        "category": "category",
        "name": "Model Name",
        "link": "url",
        "is_replacement": true/false,
        "reasoning": "why"
      }}
    ]
    """
    
    # NEW: Updated call structure for google-genai
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        )
    )
    return response.parsed # The new SDK can auto-parse JSON if you use schemas, or use .text

def run_pipeline():
    # Load current data
    if os.path.exists('ai_models.json'):
        with open('ai_models.json', 'r') as f:
            data = json.load(f)
    else:
        data = {"last_processed_video_id": "", "categories": {}}

    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    
    latest_video = feed.entries[0]
    v_id = latest_video.yt_videoid
    
    if v_id == data.get('last_processed_video_id'):
        print("Everything is up to date.")
        return

    print(f"Analyzing: {latest_video.title}")
    transcript = get_transcript(v_id)
    
    # Analysis
    raw_results = analyze_with_gemini(latest_video.title, latest_video.description, transcript)
    
    # The new SDK returns text you need to parse if not using a schema
    analysis_results = json.loads(raw_results.text) if hasattr(raw_results, 'text') else raw_results

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
