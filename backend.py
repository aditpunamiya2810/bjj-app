import time
import json
import os
import subprocess
import google.generativeai as genai
from prompt_template import get_bjj_analysis_prompt

def compress_video_locally(input_path, output_path, status_callback):
    """
    Bypasses Python memory limits and uses native Linux FFmpeg to instantly 
    crush massive 4K/60fps videos down to tiny files.
    """
    try:
        status_callback("⚡ Compressing video locally (Cloud hardware accelerated, 480p, 15fps)...")
        
        # Use the native Linux FFmpeg installed via packages.txt
        ffmpeg_exe = "ffmpeg"
        
        # Command: Overwrite (-y), Input (-i), Scale to 480p height (-vf), 15 FPS (-r), No Audio (-an)
        cmd = [
            ffmpeg_exe, "-y", "-i", input_path, 
            "-vf", "scale=-2:480", "-r", "15", "-an", output_path
        ]
        
        # Execute the command silently
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            raise Exception("Output file was empty.")
            
    except Exception as e:
        print(f"Compression failed: {e}")
        status_callback("⚠️ Compression failed. Attempting to upload original file...")
        return input_path

# ... (the rest of your analyze_video_with_gemini function stays exactly the same)

def analyze_video_with_gemini(video_path, user_desc, user_belt, opp_desc, opp_belt, api_key, status_callback=None):
    def update_status(msg):
        if status_callback:
            status_callback(msg)

    compressed_path = video_path + "_compressed.mp4"
    video_file = None

    try:
        genai.configure(api_key=api_key)

        # 1. Compress Video
        upload_path = compress_video_locally(video_path, compressed_path, update_status)
        
        # Calculate file size for debugging
        file_size_mb = os.path.getsize(upload_path) / (1024 * 1024)
        update_status(f"Uploading optimized video ({file_size_mb:.1f} MB) to Google's servers...")

        # 2. Upload Video with Retry Logic (Protects against SSL/EOF drops)
        for attempt in range(3):
            try:
                video_file = genai.upload_file(path=upload_path)
                break  # Success, break out of the retry loop
            except Exception as e:
                if attempt == 2: raise  # If it fails 3 times, crash
                update_status(f"Upload connection dropped. Retrying... ({attempt+1}/3)")
                time.sleep(2)
        
        # 3. Wait for processing to complete
        update_status("Extracting frames and processing video content...")
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise Exception("Video processing failed on Google's servers.")

        # 4. Generate Prompt
        prompt = get_bjj_analysis_prompt(user_desc, user_belt, opp_desc, opp_belt)

        # 5. Initialize Model 
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.1, 
                "response_mime_type": "application/json"
            }
        )

        # 6. Call API with Retry Logic and Explicit Extended Timeout
        update_status("Analyzing micro-battles and formatting Coach Notes (This takes ~15-30 seconds)...")
        for attempt in range(3):
            try:
                # request_options timeout prevents the connection from closing prematurely
                response = model.generate_content(
                    [video_file, prompt],
                    request_options={"timeout": 600} 
                )
                break  # Success
            except Exception as e:
                if attempt == 2: raise
                update_status(f"Analysis connection dropped. Retrying... ({attempt+1}/3)")
                time.sleep(2)

        result_json = json.loads(response.text)
        return result_json

    except Exception as e:
        # Pass the exact error string up to the UI
        raise Exception(f"{str(e)}")
    
    finally:
        # Cleanup cloud file
        if video_file:
            try:
                update_status("Cleaning up temporary cloud files...")
                genai.delete_file(video_file.name)
            except:
                pass
                
        # Cleanup local compressed file safely
        if os.path.exists(compressed_path):
            try:
                time.sleep(1)
                os.remove(compressed_path)
            except:

                pass
