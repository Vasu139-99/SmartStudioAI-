import os
import uuid
import google.generativeai as genai
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    vfx
)
from gtts import gTTS
from config.settings import GEMINI_API_KEY


class SmartStudioPipeline:

    def __init__(self):
        self.output_folder = "outputs"
        os.makedirs(self.output_folder, exist_ok=True)

        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)

    # ---------------------------------------------------
    # 1️⃣ Gemini 2.5 Flash Script Generator
    # ---------------------------------------------------
    def generate_script(self, prompt):

        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(
            f"""
            Create a powerful, cinematic 20-second product advertisement script.

            Product: {prompt}

            Style:
            - Emotional
            - Premium
            - Short sentences
            - Strong hook
            - Perfect for voice-over narration
            """
        )

        return response.text.strip()

    # ---------------------------------------------------
    # 2️⃣ gTTS Voice Generator (FREE & STABLE)
    # ---------------------------------------------------
    def generate_voice(self, script):

        audio_filename = str(uuid.uuid4()) + ".mp3"
        audio_path = os.path.join(self.output_folder, audio_filename)

        tts = gTTS(text=script, lang="en")
        tts.save(audio_path)

        return audio_path

    # ---------------------------------------------------
    # 3️⃣ Ken Burns 3D Zoom + Fade Effect
    # ---------------------------------------------------
    def create_video_from_images(self, images):

        clips = []

        for img_path in images:

            clip = ImageClip(img_path).set_duration(4)

            # Ken Burns zoom
            zoom = clip.fx(
                vfx.resize,
                lambda t: 1 + 0.05 * t
            )

            zoom = zoom.fadein(1).fadeout(1)

            clips.append(zoom)

        final_video = concatenate_videoclips(
            clips,
            method="compose"
        )

        return final_video

    # ---------------------------------------------------
    # 4️⃣ Main Pipeline
    # ---------------------------------------------------
    def run_pipeline(self, images, prompt):

        print("Generating script with Gemini 2.5 Flash...")
        script = self.generate_script(prompt)

        print("Generating voice with gTTS...")
        audio_path = self.generate_voice(script)

        print("Creating cinematic video...")
        video_clip = self.create_video_from_images(images)

        print("Adding audio...")
        audio_clip = AudioFileClip(audio_path)
        final_video = video_clip.set_audio(audio_clip)

        output_filename = str(uuid.uuid4()) + ".mp4"
        output_path = os.path.join(self.output_folder, output_filename)

        print("Rendering final video...")

        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac"
        )

        return f"outputs/{output_filename}"