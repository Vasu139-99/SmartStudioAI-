import os
import requests
from gtts import gTTS
from pydub import AudioSegment
from config.settings import settings


def generate_voice(script, output_path, language="English", target_duration=None):
    """
    Generate voiceover audio.
    """

    # Try ElevenLabs first
    if settings.ELEVENLABS_API_KEY:
        result = _elevenlabs_generate(script, output_path)
        if result:
            if target_duration:
                _pad_audio(output_path, target_duration)
            return result
        print("  [Voice] ElevenLabs failed, falling back to gTTS...")

    # Fallback: gTTS
    res = _gtts_generate(script, output_path, language)
    if res and target_duration:
        _pad_audio(output_path, target_duration)
    return res


def _elevenlabs_generate(script, output_path):
    """Generate voice using ElevenLabs API."""
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": settings.ELEVENLABS_API_KEY
        }
        data = {
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.6,
                "similarity_boost": 0.7
            }
        }

        response = requests.post(url, json=data, headers=headers, timeout=60)

        if response.status_code != 200:
            print(f"  [Voice] ElevenLabs Error ({response.status_code}): {response.text[:200]}")
            return None

        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"  [Voice] ✅ ElevenLabs voice saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"  [Voice] ElevenLabs Exception: {e}")
        return None


def _gtts_generate(script, output_path, language="English"):
    """Generate voice using Google Text-to-Speech (free fallback)."""
    # Map common language names to ISO 639-1 codes for gTTS
    lang_map = {
        "English": "en",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Portuguese": "pt",
        "Hindi": "hi",
        "Gujarati": "gu",
        "Japanese": "ja",
        "Korean": "ko"
    }
    lang_code = lang_map.get(language, "en")

    try:
        tts = gTTS(text=script, lang=lang_code, slow=False)
        tts.save(output_path)
        print(f"  [Voice] gTTS voice saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"  [Voice] gTTS Failed: {e}")
        return None


def _pad_audio(audio_path, target_duration_seconds):
    """Pad audio with silence if shorter than target duration."""
    try:
        audio = AudioSegment.from_mp3(audio_path)
        audio_duration = len(audio) / 1000  # ms to seconds

        if audio_duration < target_duration_seconds:
            silence_ms = int((target_duration_seconds - audio_duration) * 1000)
            audio += AudioSegment.silent(duration=silence_ms)
            audio.export(audio_path, format="mp3")
            print(f"  [Voice] Padded audio to {target_duration_seconds:.1f}s (was {audio_duration:.1f}s)")

    except Exception as e:
        print(f"  [Voice] Audio padding failed: {e}")