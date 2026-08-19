import os
import json
import subprocess
import google.generativeai as genai
from gtts import gTTS
from faster_whisper import WhisperModel

def get_script_from_ai(api_key: str, topic: str, target_seconds: int):
    genai.configure(api_key=api_key)
    target_words = int(target_seconds * 2.6)
    
    prompt = f"""
    Bạn là chuyên gia viết kịch bản YouTube Shorts. Viết kịch bản về chủ đề: "{topic}".
    YÊU CẦU:
    - Kịch bản đọc khoảng {target_words} từ.
    - Giọng văn lôi cuốn, giật gân, giữ chân người xem.
    Trả về định dạng JSON thuần duy nhất:
    {{
      "script_text": "Toàn bộ đoạn văn bản kịch bản tiếng Việt viết liền mạch..."
    }}
    """
    
    model = genai.GenerativeModel("gemini-3.6-flash")
    res = model.generate_content(prompt)
    clean_json = res.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)["script_text"]

def generate_voice(text: str, output_path="temp/voice.mp3"):
    os.makedirs("temp", exist_ok=True)
    tts = gTTS(text=text, lang="vi", slow=False)
    tts.save(output_path)
    return output_path

def generate_srt(audio_path, output_srt="temp/subtitles.srt"):
    os.makedirs("temp", exist_ok=True)
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="vi")
    
    def fmt_time(sec):
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    lines = []
    idx = 1
    for seg in segments:
        lines.append(str(idx))
        lines.append(f"{fmt_time(seg.start)} --> {fmt_time(seg.end)}")
        lines.append(seg.text.strip().upper())
        lines.append("")
        idx += 1
        
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_srt

def render_ffmpeg(bg_path, audio_path, srt_path, output_path="temp/final_short.mp4"):
    os.makedirs("temp", exist_ok=True)
    srt_clean = srt_path.replace("\\", "/").replace(":", "\\:")
    
    # Render video mượt mà, hỗ trợ cả phụ đề SRT trực tiếp
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,
        "-i", audio_path,
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles={srt_clean}",
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Nếu hệ thống thiếu libsubtitles, tự động fallback sang chế độ video hình ảnh + âm thanh chuẩn 100%
    if res.returncode != 0:
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg_path,
            "-i", audio_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_fallback, check=True)
        
    return output_path

def process_video_pipeline(api_key, mode, topic, custom_script, target_duration, banner_title, status_tracker):
    if "AI tự động viết" in mode or "AI tự sinh" in mode:
        status_tracker.write("📝 Đang dùng Gemini AI tạo kịch bản chuẩn thời lượng...")
        script_text = get_script_from_ai(api_key, topic, target_duration)
    else:
        status_tracker.write("📝 Đang nạp kịch bản tùy chỉnh của bạn...")
        script_text = custom_script
        
    status_tracker.write("🎙️ Đang tạo giọng đọc tiếng Việt...")
    audio_path = generate_voice(script_text)
    
    status_tracker.write("✨ Đang trích xuất thời gian phụ đề tự động...")
    srt_path = generate_srt(audio_path)
    
    status_tracker.write("🎞️ Đang render video Shorts hoàn chỉnh...")
    bg_image = "bg.jpg"
    
    output_video = render_ffmpeg(bg_image, audio_path, srt_path)
    return output_video
 
