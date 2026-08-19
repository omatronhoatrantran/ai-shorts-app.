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
    model = genai.GenerativeModel("gemini-1.5-flash")
    res = model.generate_content(prompt)
    clean_json = res.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)["script_text"]

def generate_voice(text: str, output_path="temp/voice.mp3"):
    os.makedirs("temp", exist_ok=True)
    tts = gTTS(text=text, lang="vi", slow=False)
    tts.save(output_path)
    return output_path

def generate_ass_subtitles(audio_path, output_ass="temp/subtitles.ass"):
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="vi", word_timestamps=True)
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeHighlight,Arial,85,&H00FFFFFF,&H00EB67F2,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,14,0,2,20,20,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    def fmt(sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        cs = int(round((sec - int(sec)) * 100))
        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

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

def render_ffmpeg(bg_path, audio_path, ass_path, banner_text, logo_path, output_path="temp/final_short.mp4"):
    ass_path_clean = ass_path.replace("\\", "/").replace(":", "\\:")
    
    if os.path.exists(logo_path):
        filter_str = (
            "[0:v]scale=8000:-1,zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1080x1920:fps=30[bg];"
            "[2:v]scale=150:-1[logo];"
            "[bg][logo]overlay=40:60[v_logo];"
            f"[v_logo]drawtext=text='{banner_text}':fontcolor=white:fontsize=48:"
            f"box=1:boxcolor=black@0.65:boxborderw=18:x=(w-text_w)/2:y=240[v_banner];"
            f"[v_banner]ass='{ass_path_clean}'[v_final]"
        )
        input_args = ["-loop", "1", "-i", bg_path, "-i", audio_path, "-i", logo_path]
    else:
        filter_str = (
            "[0:v]scale=8000:-1,zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1080x1920:fps=30[bg];"
            f"[bg]drawtext=text='{banner_text}':fontcolor=white:fontsize=48:"
            f"box=1:boxcolor=black@0.65:boxborderw=18:x=(w-text_w)/2:y=240[v_banner];"
            f"[v_banner]ass='{ass_path_clean}'[v_final]"
        )
        input_args = ["-loop", "1", "-i", bg_path, "-i", audio_path]

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_str,
        "-map", "[v_final]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path

def process_video_pipeline(api_key, mode, topic, custom_script, target_duration, banner_title, status_tracker):
    if "AI tự sinh" in mode:
        status_tracker.write("📝 Đang dùng Gemini AI tạo kịch bản chuẩn thời lượng...")
        script_text = get_script_from_ai(api_key, topic, target_duration)
    else:
        status_tracker.write("📝 Đang nạp kịch bản tùy chỉnh của bạn...")
        script_text = custom_script
        
    status_tracker.write("🎙️ Đang tạo giọng đọc tiếng Việt...")
    audio_path = generate_voice(script_text)
    
    status_tracker.write("✨ Đang trích xuất timestamp và tạo hiệu ứng phụ đề nảy chữ...")
    ass_path = generate_ass_subtitles(audio_path)
    
    status_tracker.write("🎞️ Đang render video: Ghép Zoom, Banner và hiệu ứng...")
    bg_image = "bg.jpg"
    logo_image = "logo.png"
    
    output_video = render_ffmpeg(bg_image, audio_path, ass_path, banner_title, logo_image)
    return output_video
