import requests
import time
import json
import random
import os
from PIL import Image, ImageFilter
from config.settings import settings

DEAPI_BASE = "https://api.deapi.ai/api/v1/client"
DEAPI_IMG2VIDEO = f"{DEAPI_BASE}/img2video"
MAX_POLL_ATTEMPTS = 60
MAX_RETRIES = 5

# Key rotation state
_current_key_idx = 0


def _get_current_key():
    """Get the current API key from the rotation pool."""
    global _current_key_idx
    keys = settings.DEAPI_KEYS
    if not keys:
        return None
    return keys[_current_key_idx % len(keys)]


def _rotate_key():
    """Rotate to the next API key and return it."""
    global _current_key_idx
    _current_key_idx += 1
    keys = settings.DEAPI_KEYS
    if not keys:
        return None
    new_key = keys[_current_key_idx % len(keys)]
    key_num = (_current_key_idx % len(keys)) + 1
    print(f"  [DeAPI] 🔄 Rotating to API Key #{key_num}/{len(keys)}")
    return new_key


def preprocess_image(image_path, output_path, width=432, height=768):
    """
    Convert any image to safe format (e.g. 432x768 or 768x432).
    Creates a blurred background with the original image centered on top.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        target_w = width
        target_h = height

        # Create blurred background
        bg = img.resize((target_w, target_h), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(30))

        # Scale foreground to fit within target
        scale = min(target_w / w, target_h / h)
        fg = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # Center foreground on background
        x = (target_w - fg.width) // 2
        y = (target_h - fg.height) // 2
        bg.paste(fg, (x, y))

        bg.save(output_path)
        print(f"  [DeAPI] Preprocessed image: {output_path} ({target_w}x{target_h})")
        return output_path

    except Exception as e:
        print(f"  [DeAPI] Image preprocessing failed: {e}")
        return None


def generate_video_from_image(image_path, prompt, output_path, width=432, height=768, temp_folder=None):
    """
    Send an image + motion prompt to DeAPI img2video endpoint.
    """
    global _current_key_idx

    # Preprocess image to safe vertical format
    if temp_folder:
        safe_image_path = os.path.join(temp_folder, f"safe_{os.path.basename(image_path)}")
    else:
        safe_image_path = os.path.join(os.path.dirname(image_path), f"safe_{os.path.basename(image_path)}")

    preprocessed = preprocess_image(image_path, safe_image_path, width, height)
    if not preprocessed:
        print(f"  [DeAPI] Preprocessing failed, using original image")
        safe_image_path = image_path

    request_id = None

    for retry in range(MAX_RETRIES):
        current_key = _get_current_key()
        if not current_key:
            print("  [DeAPI] Error: No DEAPI keys found in .env")
            return None

        headers = {
            "Authorization": f"Bearer {current_key}"
        }

        try:
            with open(safe_image_path, "rb") as img_file:
                files = {"first_frame_image": img_file}

                data = {
                    "prompt": prompt,
                    "model": "Ltxv_13B_0_9_8_Distilled_FP8",
                    "width": width,
                    "height": height,
                    "fps": 30,
                    "frames": 120,
                    "steps": 1,
                    "guidance": 8,
                    "seed": random.randint(1, 99999999),
                    "motion": "cinematic",
                }

                key_num = (_current_key_idx % len(settings.DEAPI_KEYS)) + 1 if settings.DEAPI_KEYS else 0
                print(f"  [DeAPI] Sending request (attempt {retry+1}/{MAX_RETRIES}, key #{key_num})...")

                response = requests.post(
                    DEAPI_IMG2VIDEO,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=60
                )

            print(f"  [DeAPI] Status: {response.status_code}")

            # Handle rate limiting
            if response.status_code == 429:
                print(f"  [DeAPI] ⚠️ Rate limited (429)!")
                if len(settings.DEAPI_KEYS) > 1:
                    print(f"  [DeAPI] ⏳ Waiting 20s before rotating key...")
                    time.sleep(20)
                    _rotate_key()
                else:
                    wait_time = 30 * (retry + 1)
                    print(f"  [DeAPI] ⏳ Single key - waiting {wait_time}s... (retry {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                continue

            if response.status_code != 200:
                print(f"  [DeAPI] Error ({response.status_code}): {response.text[:300]}")
                if retry < MAX_RETRIES - 1:
                    time.sleep(10)
                    continue
                return None

            result = response.json()

            # Check for "Too Many Attempts" in response body
            if "message" in result and "Too Many Attempts" in str(result.get("message", "")):
                print(f"  [DeAPI] ⚠️ Rate Limit in response body!")
                if len(settings.DEAPI_KEYS) > 1:
                    print(f"  [DeAPI] ⏳ Waiting 20s before rotating key...")
                    time.sleep(20)
                    _rotate_key()
                else:
                    wait_time = 30 * (retry + 1)
                    print(f"  [DeAPI] ⏳ Single key - waiting {wait_time}s...")
                    time.sleep(wait_time)
                continue

            try:
                request_id = result["data"]["request_id"]
                print(f"  [DeAPI] Got request_id: {request_id}")
            except (KeyError, TypeError):
                print(f"  [DeAPI] No request_id: {result}")
                if retry < MAX_RETRIES - 1:
                    time.sleep(10)
                    continue
                return None

            break

        except Exception as e:
            print(f"  [DeAPI] Exception: {e}")
            if retry < MAX_RETRIES - 1:
                time.sleep(10)
                continue
            return None
    else:
        print("  [DeAPI] All retries exhausted")
        return None

    if not request_id:
        return None

    # Poll for completion
    poll_headers = {"Authorization": f"Bearer {_get_current_key()}"}
    status_url = f"{DEAPI_BASE}/request-status/{request_id}"
    print(f"  [DeAPI] Polling {request_id}...")

    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            status_response = requests.get(status_url, headers=poll_headers, timeout=30)
            status_data = status_response.json()

            progress = status_data.get("data", {}).get("progress", 0)
            status = status_data.get("data", {}).get("status", "")

            if attempt % 5 == 0:
                print(f"  [DeAPI] Poll #{attempt+1}: progress={progress}%, status={status}")

            if progress >= 100 or status == "completed":
                data_obj = status_data.get("data", {})
                video_url = None

                if data_obj.get("result_url"):
                    video_url = data_obj["result_url"]
                elif isinstance(data_obj.get("output"), dict) and data_obj["output"].get("video_url"):
                    video_url = data_obj["output"]["video_url"]
                elif data_obj.get("video_url"):
                    video_url = data_obj["video_url"]

                if video_url:
                    video_data = requests.get(video_url, timeout=120).content
                    with open(output_path, "wb") as f:
                        f.write(video_data)
                    print(f"  [DeAPI] ✅ Saved: {output_path} ({len(video_data)} bytes)")
                    return output_path
                else:
                    print(f"  [DeAPI] No URL in: {json.dumps(status_data)[:300]}")
                    return None

            if status == "failed":
                print(f"  [DeAPI] ❌ FAILED: {json.dumps(status_data)[:300]}")
                return None

        except Exception as e:
            print(f"  [DeAPI] Poll error: {e}")

        time.sleep(5)

    print("  [DeAPI] Timeout")
    return None