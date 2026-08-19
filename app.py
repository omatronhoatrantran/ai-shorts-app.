import streamlit as st
import os
from pipeline import process_video_pipeline

st.set_page_config(page_title="AI Shorts Creator Pro", page_icon="⚡", layout="wide")

st.title("⚡ AI Video Generator Pro")
st.caption("Công cụ sản xuất video Shorts tự động: Hiệu ứng Ken Burns, Chữ nảy Karaoke & Tải về trực tiếp.")

col_input, col_preview = st.columns([1, 1])

with col_input:
    api_key = st.text_input("🔑 Gemini API Key:", type="password", placeholder="Dán mã API Key vào đây...")
    banner_title = st.text_input("📌 Tiêu đề Header Banner:", placeholder="Ví dụ: 7 SỰ THẬT KHÓ TIN VỀ ÚC")
    
    mode = st.radio("🛠️ Phương thức tạo nội dung:", ["🤖 AI tự sinh kịch bản từ chủ đề", "✍️ Tự dán kịch bản có sẵn"], horizontal=True)
    
    if mode == "🤖 AI tự sinh kịch bản từ chủ đề":
        topic = st.text_input("Nhập chủ đề:", placeholder="Ví dụ: Những bí ẩn dưới đáy biển sâu")
        target_duration = st.slider("Thời lượng mong muốn (giây):", min_value=20, max_value=60, value=35, step=5)
        custom_script = ""
    else:
        topic = ""
        target_duration = 0
        custom_script = st.text_area(
            "Dán toàn bộ kịch bản tiếng Việt của bạn vào đây:",
            placeholder="Australia là nơi có nhiều lạc đà hoang dã nhất thế giới...",
            height=180
        )
    
    btn_start = st.button("🚀 Bắt Đầu Tạo Video", type="primary", use_container_width=True)

with col_preview:
    st.subheader("📺 Video Thành Phẩm")
    preview_box = st.empty()
    status_box = st.empty()

if btn_start:
    if not api_key:
        st.error("Vui lòng điền Gemini API Key để tiếp tục!")
    elif not banner_title:
        st.error("Vui lòng nhập tiêu đề Header Banner!")
    elif mode == "🤖 AI tự sinh kịch bản từ chủ đề" and not topic:
        st.error("Vui lòng nhập chủ đề video!")
    elif mode == "✍️ Tự dán kịch bản có sẵn" and not custom_script.strip():
        st.error("Vui lòng dán nội dung kịch bản!")
    else:
        status_tracker = st.status("Đang khởi chạy pipeline...", expanded=True)
        
        try:
            output_file = process_video_pipeline(
                api_key=api_key,
                mode=mode,
                topic=topic,
                custom_script=custom_script,
                target_duration=target_duration,
                banner_title=banner_title,
                status_tracker=status_tracker
            )
            
            status_tracker.update(label="✅ Đã tạo video thành công!", state="complete", expanded=False)
            preview_box.video(output_file)
            
            with open(output_file, "rb") as f:
                st.download_button(
                    label="⬇️ Tải Video Shorts MP4",
                    data=f,
                    file_name="final_short.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
        except Exception as e:
            status_tracker.update(label=f"❌ Lỗi: {str(e)}", state="error")
            st.error(f"Chi tiết lỗi: {e}")
