import time
import os
from google import genai
from google.genai import types
from PIL import Image

# 1. Initialize the Client
client = genai.Client(api_key="YOUR_API_KEY")

def get_ui_prompt_with_retries(image_path, output_txt="ui_recreation_prompt.txt"):
    """
    Analyzes a UI screenshot and saves the recreation prompt to a text file.
    Includes exponential backoff to handle 429 Resource Exhausted errors.
    """
    max_retries = 5
    img = Image.open(image_path)
    
    # Your specific UI Analysis Prompt
    user_prompt = (
        "Analyze this UI screenshot. Generate a high-fidelity image generation "
        "prompt to recreate this design. Focus on layout, design system, and "
        "UI elements."
    )
    
    # System instruction to ensure clean output
    sys_instr = "Output ONLY the image generation prompt. No conversational filler."

    for attempt in range(max_retries + 1):
        try:
            # Generate response
            response = client.models.generate_content(
                model="gemini-2.0-flash", # Best for free tier text-to-text
                contents=[user_prompt, img],
                config=types.GenerateContentConfig(
                    system_instruction=sys_instr,
                    temperature=0.2
                )
            )

            # Success: Save and return
            prompt_text = response.text
            with open(output_txt, "w", encoding="utf-8") as f:
                f.write(prompt_text)
            
            print(f"Success! Prompt saved to {output_txt}")
            return prompt_text

        except Exception as e:
            # Check if the error is a Rate Limit (429)
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries:
                    # Exponential Backoff: 2, 4, 8, 16, 32 seconds
                    delay = (2 ** (attempt + 1)) 
                    print(f"Quota exceeded. Retrying in {delay} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
            
            # If it's a different error or we've run out of retries
            print(f"Final Error: {e}")
            return None

if __name__ == "__main__":
    # Path to your desktop/mobile/web UI screenshot
    get_ui_prompt_with_retries("ui_screenshot.png")
