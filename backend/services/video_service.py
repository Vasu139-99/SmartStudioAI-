import os
from PIL import Image as _PILImage
if not hasattr(_PILImage, 'ANTIALIAS'):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    vfx
)
from config.settings import settings


def merge_video_clips(clip_paths, output_path):
    """
    Concatenate multiple video clips into one using MoviePy.
    Resizes to 1080x1920 vertical format.
    Returns output path on success, None on failure.
    """
    clips = []
    try:
        for path in clip_paths:
            try:
                clip = VideoFileClip(path)
                clips.append(clip)
            except Exception as e:
                print(f"  [Video] ❌ Failed to load or process clip {os.path.basename(path)}: {e}")
                raise e

        if not clips:
            print("No clips to merge")
            return None

        merged = concatenate_videoclips(clips, method="compose")
        merged = merged.resize((1080, 1920))

        merged.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            preset="medium",
            ffmpeg_params=["-crf", "20"],
            audio=False
        )

        merged.close()
        print(f"Merged video saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"Merge failed: {e}")
        return None

    finally:
        for clip in clips:
            try:
                clip.close()
            except:
                pass


def add_audio_to_video(video_path, audio_path, output_path):
    """
    Overlay audio (voiceover) onto the video.
    If audio is shorter, keeps the full video (audio just ends).
    If audio is longer, trims audio to video length.
    Returns output path on success, None on failure.
    """
    video = None
    audio = None
    final = None

    try:
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)

        # Loop video if audio is longer than video
        if audio.duration > video.duration:
            video = video.fx(vfx.loop, duration=audio.duration)
        elif audio.duration < video.duration:
            video = video.subclip(0, audio.duration)

        final = video.set_audio(audio)

        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            ffmpeg_params=["-crf", "20"]
        )

        print(f"Final video with audio saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"Add audio failed: {e}")
        return None

    finally:
        for obj in [video, audio, final]:
            if obj:
                try:
                    obj.close()
                except:
                    pass


def get_video_duration(video_path):
    """Get the duration of a video file in seconds."""
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"Failed to get video duration: {e}")
        return None
