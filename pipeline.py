import os
import glob
import json
import subprocess
from PIL import Image, ImageDraw
import google.generativeai as genai
from gtts import gTTS

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

def get_or_create_bg():
    # 1. Tìm file bg.jpg hoặc bất kỳ file ảnh jpg/png nào có sẵn trong thư mục
    if os.path.exists("bg.jpg"):
        return "bg.jpg"
    
    images = glob.glob("*.jpg") + glob.glob("*.png") + glob.glob("*.jpeg")
    if images:
        return images[0]
        
    # 2. Nếu chưa có ảnh nào, tự tạo ảnh nền Gradient 1080x1920
    bg_path = "temp/default_bg.jpg"
    img = Image.new("RGB", (1080, 1920), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    for y in range(1920):
        r = int(15 + (45 - 15) * (y / 1920))
        g = int(23 + (55 - 23) * (y / 1920))
        b = int(42 + (90 - 42) * (y / 1920))
        draw.line([(0, y), (1080, y)], fill=(r, g, b))
    img.save(bg_path)
    return bg_path

def render_ffmpeg(bg_path, audio_path, output_path="temp/final_short.mp4"):
    os.makedirs("temp", exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", bg_path,
        "-i", audio_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)
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
    
    status_tracker.write("🖼️ Đang chuẩn bị hình ảnh nền...")
    bg_image = get_or_create_bg()
    
    status_tracker.write("🎞️ Đang render video Shorts hoàn chỉnh...")
    output_video = render_ffmpeg(bg_image, audio_path)
    return output_video
 
