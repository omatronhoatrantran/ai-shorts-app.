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
    
    # Ưu tiên các model thế hệ mới nhất
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest"
    ]
    
    res = None
    for m_name in models_to_try:
        try:
            model = genai.GenerativeModel(m_name)
            res = model.generate_content(prompt)
            if res and res.text:
                break
        except Exception:
            continue

    if not res:
        # Tự động quét tìm mô hình khả dụng bất kỳ từ tài khoản
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                try:
                    model = genai.GenerativeModel(m.name)
                    res = model.generate_content(prompt)
                    if res and res.text:
                        break
                except Exception:
                    continue

    if not res or not res.text:
        raise RuntimeError("Không thể kết nối mô hình Gemini phù hợp.")

    clean_json = res.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)["script_text"]

def generate_voice(text: str, output_path="temp/voice.mp3"):
    os.makedirs("temp", exist_ok=True)
    tts = gTTS(text=text, lang="vi", slow=False)
    tts.save(output_path)
    return output_path

def generate_ass_subtitles(audio_path, banner_title, output_ass="temp/subtitles.ass"):
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="vi", word_timestamps=True)
    
    clean_banner = banner_title.upper().strip()

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BannerStyle,DejaVu Sans,48,&H00FFFFFF,&H00000000,&H00000000,&H99000000,-1,0,0,0,100,100,1,0,3,16,0,8,40,40,220,1
Style: KaraokeHighlight,DejaVu Sans,80,&H00FFFFFF,&H00EB67F2,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,12,0,2,30,30,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    def fmt(sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        cs = int(round((sec - int(sec)) * 100))
        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    events.append(f"Dialogue: 1,0:00:00.00,0:10:00.00,BannerStyle,,0,0,0,,{clean_banner}")

    for seg in segments:
        for w in seg.words:
            word_clean = w.word.strip().upper()
            start_t = fmt(w.start)
            end_t = fmt(w.end)
            styled = f"{{\\c&H00EB67F2&\\t(0,80,\\fscx115\\fscy115)}}{word_clean}"
            events.append(f"Dialogue: 0,{start_t},{end_t},KaraokeHighlight,,0,0,0,,{styled}")
            
    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))
    return output_ass

def render_ffmpeg(bg_path, audio_path, ass_path, output_path="temp/final_short.mp4"):
    ass_path_clean = ass_path.replace("\\", "/").replace(":", "\\:")
    
    filter_str = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"ass='{ass_path_clean}'[v_final]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,
        "-i", audio_path,
        "-filter_complex", filter_str,
        "-map", "[v_final]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
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
    
    status_tracker.write("✨ Đang tạo phụ đề Karaoke & Header Banner...")
    ass_path = generate_ass_subtitles(audio_path, banner_title)
    
    status_tracker.write("🎞️ Đang render video Shorts hoàn chỉnh...")
    bg_image = "bg.jpg"
    
    output_video = render_ffmpeg(bg_image, audio_path, ass_path)
    return output_video
