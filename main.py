import requests
import re
import time
import json
import os

# API Configuration
API_KEY = "YOUR_API_KEY" 
GEMINI_MODEL = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

def get_video_summary(video_url):
    """Summarizes YouTube video using Gemini API with exponential backoff."""
    reg_exp = r"^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*"
    match = re.match(reg_exp, video_url)
    video_id = match.group(7) if (match and len(match.group(7)) == 11) else None
    
    if not video_id:
        return "Error: Invalid URL"

    payload = {
        "contents": [{"parts": [{"text": f"Summarize this: https://www.youtube.com/watch?v={video_id}"}]}],
        "systemInstruction": {"parts": [{"text": "You are an expert video analyst. Provide a concise summary."}]}
    }

    for attempt in range(6):
        try:
            response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            if response.status_code in [429, 500, 503]:
                time.sleep(2 ** attempt)
        except Exception as e:
            time.sleep(2 ** attempt)
    return "Error: Failed to fetch summary"

def update_ai_models_json(video_url, output_file="ai_models.json"):
    """Generates summary and wraps it in your specific JSON structure."""
    summary_content = get_video_summary(video_url)

    # Building the exact structure you requested
    data = {
        "summary": summary_content,
        "showLicenseMeta": False,
        "license": None,
        "newIssuePath": "/Armx-123/latest_ai/issues/new",
        "newDiscussionPath": None,
        "codeownerInfo": {
            "codeownerPath": None,
            "ownedByCurrentUser": None,
            "ownersForFile": None,
            "ruleForPathLine": None
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"File '{output_file}' has been updated with the summary and metadata.")

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    update_ai_models_json(test_url)
