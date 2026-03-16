import os
import json
from PIL import Image
from google import genai
from google.genai import types
from config.settings import settings

# Initialize Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def analyze_images_and_generate_script(image_paths, product_name="", language="English"):
    """
    Send 4 images to Google Gemini 2.5. It analyzes them and returns:
    - A voiceover script (~50 words)
    - 4 scene motion prompts (one per image for DeAPI video generation)
    """

    images = []
    try:
        for path in image_paths:
            if os.path.exists(path):
                images.append(Image.open(path))
    except Exception as e:
        print(f"Error loading images for Gemini: {e}")

    prompt_text = f"""Analyze these images for the product: {product_name if product_name else 'Unnamed Product'}.
Create:
1. A powerful voiceover script written in {language} (max 50 words, ~15 seconds when spoken). Must have a strong hook and call-to-action.
2. For EACH image, a cinematic motion prompt describing how to animate it as a 3D-style video (camera movement, lighting effects, particles, etc.)

Return ONLY valid JSON in this exact format:
{{
    "script": "Your voiceover script here",
    "scene_prompts": [
        "Scene 1 motion prompt",
        "Scene 2 motion prompt",
        "Scene 3 motion prompt",
        "Scene 4 motion prompt"
    ]
}}"""

    contents = images + [prompt_text]

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        return result

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        # Ultimate fallback
        return {
            "script": f"Experience innovation like never before with {product_name if product_name else 'our product'}. Quality you can trust.",
            "scene_prompts": [
                "Cinematic slow zoom with soft lighting and gentle particle effects",
                "Smooth camera pan with dramatic shadows and golden hour lighting",
                "Dynamic orbit shot with lens flare and depth of field blur",
                "Epic pull-back reveal with volumetric lighting and bokeh"
            ]
        }


def translate_text(text, target_language):
    """
    Translates the given text into the target language using Gemini 2.5.
    """
    if not text or target_language == "English":
        return text

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=f"Translate the following text into {target_language}. Return ONLY the translated text.\n\nText:\n{text}",
        )
        return response.text.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text