from flask import Blueprint, request, jsonify, session
import os
import time
import uuid
import json
import threading

from config.settings import settings
from database.db import create_project, update_project, get_project, get_all_projects, delete_project
from services.gemini_service import analyze_images_and_generate_script
from services.deapi_service import generate_video_from_image
from services.elevenlabs_service import generate_voice
from services.video_service import merge_video_clips, add_audio_to_video, get_video_duration
from services.caption_service import generate_vtt_captions, add_captions_to_video
import shutil

project_bp = Blueprint("project_bp", __name__)


def run_pipeline(project_id, product_name, image_paths, language="English", custom_script=None, caption_color="#ffff00", width=432, height=768, aspect_ratio='9:16'):
    """
    Run the full AI video generation pipeline in a background thread.
    Updates project status at each step.
    Fails immediately if any external API fails.
    """
    try:
        # ── Step 1: Gemini analyzes images & generates script ──
        if custom_script:
            update_project(project_id, current_step="Using custom script...", status="processing")
            print(f"\n[{project_id}] Step 1: Using custom script (Language: {language})...")
            script = custom_script
            scene_prompts = [f"Cinematic high quality footage of {product_name}"] * 4
        else:
            update_project(project_id, current_step="Analyzing images with AI...", status="processing")
            print(f"\n[{project_id}] Step 1: Gemini analyzing images (Language: {language})...")

            result = analyze_images_and_generate_script(image_paths, product_name, language)
            script = result.get("script", "")
            scene_prompts = result.get("scene_prompts", [])

        if not script:
            update_project(project_id, status="failed", error_message="Gemini failed to generate script")
            return

        # Ensure we have exactly 4 prompts
        while len(scene_prompts) < 4:
            scene_prompts.append("Cinematic slow zoom with soft lighting")

        update_project(
            project_id,
            script=script,
            scene_prompts=json.dumps(scene_prompts),
            current_step="Script generated! Creating videos..."
        )
        print(f"[{project_id}] Script: {script[:100]}...")

        # ── Step 2: DeAPI generates 3D video from each image (Strict) ──
        temp_folder = os.path.join(settings.TEMP_FOLDER, project_id)
        os.makedirs(temp_folder, exist_ok=True)

        clip_paths = []

        for i in range(4):
            update_project(project_id, current_step=f"Generating 3D video {i+1}/4...")
            print(f"[{project_id}] Step 2.{i+1}: DeAPI generating video for image {i+1}...")

            clip_path = os.path.join(temp_folder, f"clip_{i+1}.mp4")

            result_path = generate_video_from_image(
                image_paths[i],
                scene_prompts[i],
                clip_path,
                width=width,
                height=height,
                temp_folder=temp_folder
            )

            if not result_path:
                print(f"[{project_id}] DeAPI failed on image {i+1}. Aborting pipeline.")
                update_project(project_id, status="failed", error_message=f"DeAPI video generation failed on image {i+1}")
                return

            clip_paths.append(result_path)

        # ── Step 3: MoviePy merges DeAPI clips ──
        update_project(project_id, current_step="Merging video clips...")
        print(f"[{project_id}] Step 3: Merging {len(clip_paths)} clips...")

        merged_path = os.path.join(temp_folder, "merged.mp4")
        merge_result = merge_video_clips(clip_paths, merged_path)

        if not merge_result:
            update_project(project_id, status="failed", error_message="Video merge failed")
            return

        # ── Step 4: Voice generation (ElevenLabs → gTTS fallback) ──
        update_project(project_id, current_step="Generating voiceover...")
        print(f"[{project_id}] Step 4: Generating voice...")

        # Get merged video duration for logging only
        video_duration = get_video_duration(merged_path)

        voice_path = os.path.join(temp_folder, "voice.mp3")
        voice_result = generate_voice(script, voice_path, language=language)

        if not voice_result:
            print(f"[{project_id}] Voice generation failed. Aborting pipeline.")
            update_project(project_id, status="failed", error_message="Voice generation failed (both ElevenLabs and gTTS)")
            return

        # Save base video (no audio) for future remixing
        base_video_filename = f"{project_id}_base.mp4"
        base_video_path = os.path.join(settings.OUTPUT_FOLDER, base_video_filename)
        shutil.copy2(merged_path, base_video_path)
        print(f"[{project_id}] Step 4: Silent base video saved to {base_video_filename}")

        # ── Step 5: MoviePy adds voice to video ──
        update_project(project_id, current_step="Adding voiceover to video...")
        print(f"[{project_id}] Step 5: Adding audio to video...")

        video_with_audio_path = os.path.join(temp_folder, "with_audio.mp4")
        final_result = add_audio_to_video(merged_path, voice_path, video_with_audio_path)

        if not final_result:
            update_project(project_id, status="failed", error_message="Failed to add audio to video")
            return

        # ── Step 6: Generate translated VTT captions ──
        update_project(project_id, current_step="Generating translated CC captions...")
        print(f"[{project_id}] Step 6: Generating translated VTT captions...")

        final_filename = f"{project_id}.mp4"
        final_path = os.path.join(settings.OUTPUT_FOLDER, final_filename)

        # Skip hardcoded SRT burning entirely, copy video_with_audio to final_path
        shutil.copy2(video_with_audio_path, final_path)

        vtt_dict = generate_vtt_captions(video_with_audio_path, settings.OUTPUT_FOLDER, project_id)
        
        # Burn subtitle for download
        burned_filename = f"{project_id}_burned.mp4"
        burned_path = os.path.join(settings.OUTPUT_FOLDER, burned_filename)
        
        vtt_to_burn = None
        if language in vtt_dict:
            vtt_to_burn = vtt_dict[language]
        elif "English" in vtt_dict:
            vtt_to_burn = vtt_dict["English"]
        elif vtt_dict:
            vtt_to_burn = list(vtt_dict.values())[0]

        if vtt_to_burn:
            vtt_full_path = os.path.join(settings.OUTPUT_FOLDER, vtt_to_burn)
            print(f"[{project_id}] Burning captions {vtt_to_burn} to {burned_filename} for download")
            add_captions_to_video(video_with_audio_path, vtt_full_path, burned_path, caption_color=caption_color)
            download_url = f"/static/output/{burned_filename}"
        else:
            download_url = f"/static/output/{final_filename}"
        
        # ── Done ──
        video_url = f"/static/output/{final_filename}"
        vtt_paths_json = json.dumps(vtt_dict)

        update_project(
            project_id,
            status="completed",
            current_step="Done!",
            video_path=video_url,
            download_path=download_url,
            vtt_paths=vtt_paths_json,
            voice_path=f"/temp/{project_id}/voice.mp3",
            script=script
        )

        print(f"[{project_id}] ✅ Pipeline complete! Video: {video_url}")

    except Exception as e:
        import traceback
        print(f"[{project_id}] ❌ Pipeline error: {e}")
        traceback.print_exc()
        update_project(project_id, status="failed", error_message=str(e))


# ============================================
# API: Start video generation
# ============================================

@project_bp.route('/api/generate', methods=['POST'])
def generate_video():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Please login first"}), 401

        product_name = request.form.get("product_name", "Product")
        language = request.form.get("language", "English")
        custom_script = request.form.get("custom_script")
        caption_color = request.form.get("caption_color", "#ffff00")
        aspect_ratio = request.form.get("aspect_ratio", settings.DEFAULT_ASPECT_RATIO)
        images = request.files.getlist("images")

        # Get dimensions
        width, height = settings.ASPECT_RATIOS.get(aspect_ratio, settings.ASPECT_RATIOS[settings.DEFAULT_ASPECT_RATIO])

        if len(images) != 4:
            return jsonify({"error": "Please upload exactly 4 images"}), 400

        # Create project
        project_id = str(uuid.uuid4())[:8]

        # Save uploaded images
        upload_dir = os.path.join(settings.UPLOAD_FOLDER, project_id)
        os.makedirs(upload_dir, exist_ok=True)

        image_paths = []
        for i, img in enumerate(images):
            ext = os.path.splitext(img.filename)[1] or ".jpg"
            filename = f"image_{i+1}{ext}"
            path = os.path.join(upload_dir, filename)
            img.save(path)
            image_paths.append(path)

        # Create DB record linked to user
        create_project(project_id, product_name, image_paths, user_id=user_id, language=language, aspect_ratio=aspect_ratio)

        # Run pipeline in background thread
        thread = threading.Thread(
            target=run_pipeline,
            args=(project_id, product_name, image_paths, language, custom_script, caption_color, width, height, aspect_ratio)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "project_id": project_id,
            "message": "Processing started!"
        })

    except Exception as e:
        print(f"Generate error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# API: Check project status
# ============================================

@project_bp.route('/api/project/<project_id>', methods=['GET'])
def check_status(project_id):
    project = get_project(project_id)

    if not project:
        return jsonify({"error": "Project not found"}), 404

    return jsonify({
        "id": project["id"],
        "product_name": project["product_name"],
        "status": project["status"],
        "current_step": project["current_step"],
        "video_path": project["video_path"],
        "download_path": project.get("download_path", project["video_path"]),
        "vtt_paths": project.get("vtt_paths", "{}"),
        "error_message": project["error_message"],
        "created_at": project["created_at"]
    })


# ============================================
# API: Burn specific captions
# ============================================

@project_bp.route('/api/project/<project_id>/burn_captions', methods=['POST'])
def burn_specific_captions(project_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please login first"}), 401
        
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
        
    if project.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json or {}
    language_to_burn = data.get("language", "English")
    caption_color = data.get("captionColor", "#ffff00")
    
    video_path = project.get("video_path", "")
    base_video_path = os.path.join(settings.OUTPUT_FOLDER, f"{project_id}.mp4")
    
    if not os.path.exists(base_video_path):
        return jsonify({"error": "Source video not found"}), 404
        
    import json
    vtt_paths_str = project.get("vtt_paths", "{}")
    try:
        if isinstance(vtt_paths_str, str):
            vtt_paths = json.loads(vtt_paths_str)
        else:
            vtt_paths = vtt_paths_str
    except Exception:
        vtt_paths = {}
        
    if language_to_burn not in vtt_paths:
        return jsonify({"error": f"Captions for {language_to_burn} not found"}), 404
        
    vtt_filename = vtt_paths[language_to_burn]
    vtt_full_path = os.path.join(settings.OUTPUT_FOLDER, vtt_filename)
    
    if not os.path.exists(vtt_full_path):
        return jsonify({"error": "Caption file not found on disk"}), 404
        
    # Generate new burned MP4
    from services.caption_service import add_captions_to_video
    burned_filename = f"{project_id}_burned_{language_to_burn}.mp4"
    burned_path = os.path.join(settings.OUTPUT_FOLDER, burned_filename)
    
    print(f"[{project_id}] Dynamically burning {language_to_burn} captions to {burned_filename}")
    add_captions_to_video(base_video_path, vtt_full_path, burned_path, caption_color=caption_color)
    
    download_url = f"/static/output/{burned_filename}"
    
    return jsonify({
        "success": True,
        "download_url": download_url
    })


# ============================================
# API: Remix Audio & Style
# ============================================

@project_bp.route('/api/project/<project_id>/remix', methods=['POST'])
def remix_project(project_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please login first"}), 401
    
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    if project.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    new_language = data.get("language", "English")
    caption_color = data.get("captionColor", "#ffff00")
    new_aspect_ratio = data.get("aspectRatio") # Optional, only if they want to change size
    
    print(f"[{project_id}] 🎛️ Remixing project: language={new_language}, color={caption_color}, size={new_aspect_ratio}")
    
    try:
        # If aspect ratio changed, we MUST re-generate the clips
        if new_aspect_ratio and new_aspect_ratio in settings.ASPECT_RATIOS:
            # Check if it's actually different from what we might have saved (though we don't save it yet)
            # For now, let's assume if it's provided, they want a full re-render
            print(f"[{project_id}] 🔄 Aspect Ratio change detected to {new_aspect_ratio}. Re-generating scenery...")
            
            width, height = settings.ASPECT_RATIOS[new_aspect_ratio]
            
            # Re-run pipeline for this project (it will overwrite existing files)
            product_name = project.get("product_name", "Product")
            image_paths = json.loads(project.get("image_paths", "[]"))
            
            # Since remix should be fast if only audio, but full if aspect ratio changes, 
            # we run it here and Return early with a 'processing' signal or just wait.
            # The user expects 'Apply & Remix' to be a process.
            # For simplicity, we'll run the pipeline synchronously for the remix if it's a full re-render
            # OR better: run_pipeline in background and return 202.
            # But the UI expects a result. Let's run it in thread and tell UI to poll.
            
            update_project(project_id, status="processing")
            thread = threading.Thread(
                target=run_pipeline,
                args=(project_id, product_name, image_paths, new_language, project.get("script"), caption_color, width, height)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "processing": True,
                "message": "Full re-render started for new aspect ratio"
            })

        # --- Standard Audio/Color Only Remix ---
        # Paths
        base_video_path = os.path.join(settings.OUTPUT_FOLDER, f"{project_id}_base.mp4")
        if not os.path.exists(base_video_path):
            return jsonify({"error": "Base silent video not found. This project might be too old for remixing."}), 400

        project_temp = os.path.join(settings.TEMP_FOLDER, project_id)
        os.makedirs(project_temp, exist_ok=True)

        # 1. Get/Translate Script
        original_script = project.get("script", "")
        original_language = project.get("language", "English")
        
        if not original_script:
             return jsonify({"error": "Original script missing in database"}), 400
        
        # Translate to new language if they are different
        from services.gemini_service import translate_text
        print(f"[{project_id}] 🔍 Remix Debug: original_lang={original_language}, new_lang={new_language}")
        
        if str(new_language).strip().lower() != str(original_language).strip().lower():
            print(f"[{project_id}] 🔄 Translating script from {original_language} to {new_language}...")
            remix_script = translate_text(original_script, new_language)
            print(f"[{project_id}] 📝 Translated Script: {remix_script[:100]}...")
            if remix_script == original_script:
                print(f"[{project_id}] ⚠️ Translation returned same text, possible fallback Node.")
        else:
            print(f"[{project_id}] 🤝 Languages match, skipping translate Node.")
            remix_script = original_script

        # 2. Generate New Voice
        from services.elevenlabs_service import generate_voice
        voice_filename = f"voice_{new_language.lower()}.mp3"
        voice_path = os.path.join(project_temp, voice_filename)
        
        # Get duration from base video
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(base_video_path)
        duration = clip.duration
        clip.close()
        
        print(f"[{project_id}] Generating {new_language} voiceover...")
        success = generate_voice(remix_script, voice_path, language=new_language, target_duration=duration)
        if not success:
            return jsonify({"error": "Voice generation failed"}), 500

        # 3. Merge with Base Video
        from services.video_service import add_audio_to_video
        merged_filename = f"{project_id}_remixed.mp4" # Temp name
        merged_path = os.path.join(project_temp, merged_filename)
        
        final_result = add_audio_to_video(base_video_path, voice_path, merged_path)
        if not final_result:
            return jsonify({"error": "Merging audio failed"}), 500
        
        # Overwrite the main video file so the player refreshes correctly
        final_video_path = os.path.join(settings.OUTPUT_FOLDER, f"{project_id}.mp4")
        shutil.copy2(merged_path, final_video_path)

        # 4. Regenerate VTTs
        from services.caption_service import generate_vtt_captions
        vtt_dict = generate_vtt_captions(final_video_path, settings.OUTPUT_FOLDER, project_id)
        
        # 5. Pre-burn the selected color for immediate download readiness
        from services.caption_service import add_captions_to_video
        burned_filename = f"{project_id}_burned.mp4"
        burned_path = os.path.join(settings.OUTPUT_FOLDER, burned_filename)
        
        vtt_to_burn = vtt_dict.get(new_language) or list(vtt_dict.values())[0] if vtt_dict else None
        if vtt_to_burn:
            vtt_full_path = os.path.join(settings.OUTPUT_FOLDER, vtt_to_burn)
            add_captions_to_video(final_video_path, vtt_full_path, burned_path, caption_color=caption_color)

        # Update DB
        update_project(project_id, 
            voice_path=voice_path, 
            vtt_paths=json.dumps(vtt_dict),
            download_path=burned_path,
            language=new_language,
            script=remix_script
        )

        return jsonify({
            "success": True,
            "video_path": f"/static/output/{project_id}.mp4?t={int(time.time())}",
            "vtt_paths": vtt_dict
        })

    except Exception as e:
        print(f"Remix error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# API: List all projects
# ============================================

@project_bp.route('/api/projects', methods=['GET'])
def list_projects():
    user_id = session.get("user_id")
    projects = get_all_projects(user_id=user_id)

    return jsonify({
        "projects": [{
            "id": p["id"],
            "product_name": p["product_name"],
            "status": p["status"],
            "video_path": p["video_path"],
            "download_path": p.get("download_path", p["video_path"]),
            "vtt_paths": p.get("vtt_paths", "{}"),
            "created_at": p["created_at"]
        } for p in projects]
    })


# ============================================
# API: Delete a project
# ============================================

@project_bp.route('/api/project/<project_id>', methods=['DELETE'])
def remove_project(project_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please login first"}), 401

    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if project.get("user_id") != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    delete_project(project_id)
    return jsonify({"message": "Project deleted successfully"})