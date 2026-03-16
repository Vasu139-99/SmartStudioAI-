import whisper
import os
import subprocess
import shutil
import imageio_ffmpeg
import tempfile
from config.settings import settings
from datetime import timedelta
from deep_translator import GoogleTranslator


def generate_captions_srt(video_path, srt_output_path):
    """
    Transcribe audio from video using Whisper with word-level timestamps.
    Generates a proper SRT file with timed word chunks.
    Returns the SRT file path on success, None on failure.
    """
    try:
        # Tell Whisper to use MoviePy's bundled ffmpeg by prepending it to the PATH
        # Create a wrapper for ffmpeg so whisper can find it by the exact name "ffmpeg.exe"
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_dir = tempfile.mkdtemp()
        ffmpeg_alias = os.path.join(temp_dir, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_alias):
            shutil.copyfile(ffmpeg_exe, ffmpeg_alias)
        os.environ["PATH"] = temp_dir + os.pathsep + os.environ.get("PATH", "")

        print(f"  [Captions] Using ffmpeg at: {ffmpeg_exe}")
        print(f"  [Captions] Loading Whisper model ({settings.WHISPER_MODEL_SIZE})...")

        model = whisper.load_model(settings.WHISPER_MODEL_SIZE)

        print("  [Captions] Transcribing audio with word timestamps...")
        result = model.transcribe(
            video_path,
            word_timestamps=True,
            verbose=False
        )

        # Generate SRT from word-level timestamps
        max_words = settings.MAX_CAPTION_WORDS
        index = 1
        srt_lines = []

        for segment in result.get("segments", []):
            words = segment.get("words", [])
            i = 0
            while i < len(words):
                chunk = words[i:i + max_words]
                if not chunk:
                    break
                start = chunk[0]["start"]
                end = chunk[-1]["end"]
                text = " ".join(w["word"].strip() for w in chunk)

                start_str = _format_srt_time(start)
                end_str = _format_srt_time(end)

                srt_lines.append(f"{index}\n{start_str} --> {end_str}\n{text}\n")
                index += 1
                i += max_words

        with open(srt_output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        print(f"  [Captions] ✅ SRT saved to {srt_output_path} ({index - 1} entries)")
        return srt_output_path

    except Exception as e:
        print(f"  [Captions] SRT generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _format_srt_time(t):
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def add_captions_to_video(video_path, srt_path, output_path, caption_color="#ffff00"):
    """
    Burn timed SRT captions into the video using FFmpeg's subtitles filter.
    Uses yellow text with black outline, positioned at bottom center.
    This is far more reliable than MoviePy TextClip (no ImageMagick needed).
    Returns output path on success, None on failure.
    """
    if not srt_path or not os.path.exists(srt_path):
        print("  [Captions] ⚠️ No SRT file found, copying video without captions.")
        shutil.copy2(video_path, output_path)
        return output_path

    # Verify SRT file has content
    srt_size = os.path.getsize(srt_path)
    if srt_size == 0:
        print("  [Captions] ⚠️ SRT file is empty, copying video without captions.")
        shutil.copy2(video_path, output_path)
        return output_path

    print(f"  [Captions] SRT file: {srt_path} ({srt_size} bytes)")

    try:
        # Get the ffmpeg executable path
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"  [Captions] Using FFmpeg: {ffmpeg_exe}")

        # Escape the SRT path for FFmpeg subtitles filter on Windows
        # FFmpeg requires forward slashes and colons escaped in filter paths
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        # Determine font based on language in the vtt filename
        filename = os.path.basename(srt_path).lower()
        font_name = "Arial"
        if "_gu.vtt" in filename or "_hi.vtt" in filename:
            font_name = "Nirmala UI"
        elif "_ja.vtt" in filename:
            font_name = "Meiryo"
        elif "_ko.vtt" in filename:
            font_name = "Malgun Gothic"
        elif "_zh.vtt" in filename: # just in case
            font_name = "Microsoft YaHei"

        # Convert hex #RRGGBB to ASS format &H00BBGGRR&
        bgr_color = "00FFFF" # Default yellow
        if caption_color and caption_color.startswith("#") and len(caption_color) == 7:
            r = caption_color[1:3]
            g = caption_color[3:5]
            b = caption_color[5:7]
            bgr_color = f"{b}{g}{r}".upper()
            
        ass_color = f"&H00{bgr_color}&"

        # Build FFmpeg subtitles filter with styling
        # FontSize is set relative to video height for consistency
        subtitle_style = (
            f"FontName={font_name},"
            "FontSize=20,"
            f"PrimaryColour={ass_color},"     # Selected Color (BGR in ASS format)
            "OutlineColour=&H000000&,"        # Black outline
            "BorderStyle=1,"                  # Outline + shadow
            "Outline=2,"                      # Outline thickness
            "Shadow=1,"                       # Shadow depth
            "Alignment=2,"                    # Bottom center
            "MarginV=30,"                     # Margin from bottom
            "Bold=1"                          # Bold text
        )

        cmd = [
            ffmpeg_exe,
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{subtitle_style}'",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",  # Overwrite output
            output_path
        ]

        print(f"  [Captions] Running FFmpeg command...")
        print(f"  [Captions] CMD: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"  [Captions] ❌ FFmpeg failed (exit code {result.returncode})")
            print(f"  [Captions] STDERR: {result.stderr[-1000:]}")

            # Fallback: copy video without captions
            shutil.copy2(video_path, output_path)
            print("  [Captions] Fallback: copied video without captions.")
            return output_path

        # Verify output file exists and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"  [Captions] ✅ Video with captions saved: {output_path}")
            return output_path
        else:
            print("  [Captions] ❌ Output file missing or empty after FFmpeg.")
            shutil.copy2(video_path, output_path)
            print("  [Captions] Fallback: copied video without captions.")
            return output_path

    except subprocess.TimeoutExpired:
        print("  [Captions] ❌ FFmpeg timed out (>5 minutes)")
        shutil.copy2(video_path, output_path)
        return output_path

    except Exception as e:
        print(f"  [Captions] ❌ Caption overlay failed: {e}")
        import traceback
        traceback.print_exc()
        shutil.copy2(video_path, output_path)
        print("  [Captions] Fallback: copied video without captions.")
        return output_path


def _format_vtt_time(seconds: float):
    """Convert float seconds to VTT timestamp format HH:MM:SS.mmm"""
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    milliseconds = delta.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def _create_vtt_from_segments(segments, output_path, lang_code='en', translator=None):
    """Writes transcription segments to a VTT file, optionally translating."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        
        for i, segment in enumerate(segments):
            start = _format_vtt_time(segment["start"])
            end = _format_vtt_time(segment["end"])
            text = segment["text"].strip()
            
            if translator:
                try:
                    text = translator.translate(text)
                except Exception as e:
                    print(f"  [Captions] Translation failed for segment {i} ({lang_code}): {e}")
                    
            f.write(f"{i + 1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")


def generate_vtt_captions(video_path, output_dir, project_id):
    """
    Transcribe audio from video using Whisper.
    Generates proper VTT files for all supported languages.
    Returns a dictionary of language names to generated VTT filenames.
    """
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_dir = tempfile.mkdtemp()
        ffmpeg_alias = os.path.join(temp_dir, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_alias):
            shutil.copyfile(ffmpeg_exe, ffmpeg_alias)
        os.environ["PATH"] = temp_dir + os.pathsep + os.environ.get("PATH", "")

        print(f"  [Captions] Loading Whisper model ({settings.WHISPER_MODEL_SIZE}) for VTT...")
        model = whisper.load_model(settings.WHISPER_MODEL_SIZE)

        print("  [Captions] Transcribing audio for VTT generation...")
        result = model.transcribe(video_path, verbose=False)
        segments = result.get("segments", [])

        if not segments:
            print("  [Captions] ⚠️ No speech detected. Skipping VTT generation.")
            return {}

        languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "hi": "Hindi",
            "gu": "Gujarati",
            "ja": "Japanese",
            "ko": "Korean"
        }

        generated_vtts = {}

        # 1. Base English
        en_vtt_filename = f"{project_id}_en.vtt"
        en_vtt_path = os.path.join(output_dir, en_vtt_filename)
        _create_vtt_from_segments(segments, en_vtt_path, lang_code="en")
        generated_vtts["English"] = en_vtt_filename
        print(f"  [Captions] ✅ Generated English VTT: {en_vtt_filename}")

        # 2. Translate other languages
        for code, name in languages.items():
            if code == "en":
                continue
                
            print(f"  [Captions] Translating to {name} ({code})...")
            try:
                translator = GoogleTranslator(source='auto', target=code)
                lang_vtt_filename = f"{project_id}_{code}.vtt"
                lang_vtt_path = os.path.join(output_dir, lang_vtt_filename)
                
                _create_vtt_from_segments(segments, lang_vtt_path, lang_code=code, translator=translator)
                generated_vtts[name] = lang_vtt_filename
                print(f"  [Captions] ✅ Generated {name} VTT: {lang_vtt_filename}")
            except Exception as e:
                print(f"  [Captions] ❌ Failed to generate {name} VTT: {e}")

        return generated_vtts

    except Exception as e:
        print(f"  [Captions] VTT generation failed: {e}")
        import traceback
        traceback.print_exc()
        return {}
