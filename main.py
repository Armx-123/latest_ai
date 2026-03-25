import os
import json
import feedparser
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# --- Configuration ---
RSS_URL = "https://youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_transcript(video_id):
    try:
        lines = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([line['text'] for line in lines])
    except Exception:
        return "Transcript not available."

def analyze_with_gemini(title, description, transcript):
    prompt = f"""
    You are an AI market analyst. Analyze this YouTube video data:
    Title: {title}
    Description: {description}
    Transcript: {transcript}

    Task:
    1. Identify all AI tools/models mentioned.
    2. Categorize them (e.g., 'Video Gen', 'LLM', 'AI Search').
    3. Find their official links in the description.
    4. Crucially: Determine if the creator claims a tool is "the new best," "better than [competitor]," or a "major breakthrough."

    Return a JSON list of objects:
    [
      {{
        "category": "category name",
        "name": "AI Model Name",
        "link": "link to AI",
        "is_replacement": true/false,
        "reasoning": "Briefly why it is better or what it does"
      }}
    ]
    """
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application_json"})
    return json.loads(response.text)

# --- Main Execution ---
def run_pipeline():
    # 1. Load State
    with open('ai_models.json', 'r') as f:
        data = json.load(f)

    # 2. Check RSS
    feed = feedparser.parse(RSS_URL)
    if not feed.entries: return
    
    latest_video = feed.entries[0]
    v_id = latest_video.yt_videoid
    
    if v_id == data.get('last_processed_video_id'):
        print("No new videos. Exiting.")
        return

    print(f"New video detected: {latest_video.title}")
    
    # 3. Gather Context
    transcript = get_transcript(v_id)
    analysis_results = analyze_with_gemini(latest_video.title, latest_video.description, transcript)

    # 4. Update JSON with "Replacement Logic"
    for item in analysis_results:
        cat = item['category']
        # Replace if: Category is new OR Gemini flagged it as a 'replacement' (better model)
        if cat not in data['categories'] or item.get('is_replacement'):
            print(f"Updating category [{cat}] with {item['name']}")
            data['categories'][cat] = {
                "name": item['name'],
                "link": item['link'],
                "video_ref": f"https://youtu.be/{v_id}",
                "reasoning": item['reasoning']
            }

    # 5. Save State
    data['last_processed_video_id'] = v_id
    with open('ai_models.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    run_pipeline()
