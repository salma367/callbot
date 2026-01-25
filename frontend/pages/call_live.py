import streamlit as st
import requests
from audiorecorder import audiorecorder
import tempfile
import os
from io import BytesIO


st.title("📞 Live Call (Voice Loop)")

st.markdown("### 🎤 Speak")
audio_bytes = audiorecorder("Start Recording", "Stop Recording")

st.markdown("### 📂 Or upload audio")
uploaded_audio = st.file_uploader("Upload audio", type=["wav", "mp3"])

audio_file_path = None


def audiosegment_to_wav_bytes(audio_segment):
    buf = BytesIO()
    audio_segment.export(buf, format="wav")
    return buf.getvalue()


# If mic recording is used
if len(audio_bytes) > 0:
    wav_bytes = audiosegment_to_wav_bytes(audio_bytes)
    st.audio(wav_bytes, format="audio/wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(wav_bytes)
        audio_file_path = f.name

# If file upload is used
elif uploaded_audio is not None:
    audio_file_path = uploaded_audio

# Send to backend
if audio_file_path and st.button("▶️ Talk"):
    with open(audio_file_path, "rb") as f:
        files = {"audio": f}
        res = requests.post("http://localhost:8000/call/voice", files=files)

    if res.ok:
        data = res.json()

        st.markdown("### 🧑 Client said")
        st.write(data["text"])

        st.markdown("### 🤖 Bot speaks")
        st.audio(data["audio_response"], format="audio/wav")

        st.markdown("### 📊 Info")
        st.write("Language:", data["language"])
        st.write("ASR confidence:", data["confidence"])
    else:
        st.error("Backend error")

# Cleanup temp file
if isinstance(audio_file_path, str) and os.path.exists(audio_file_path):
    os.remove(audio_file_path)
