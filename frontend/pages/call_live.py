import streamlit as st
import requests

st.title("📞 Live Call (Voice Loop)")

audio = st.file_uploader("🎤 Speak or upload audio", type=["wav", "mp3"])

if audio and st.button("▶️ Talk"):
    files = {"audio": audio}
    res = requests.post("http://localhost:8000/call/voice", files=files)

    if res.ok:
        data = res.json()

        st.markdown("### 🧑 Client said")
        st.write(data["text"])

        st.markdown("### 🤖 Bot speaks")
        st.audio(data["audio_response"])

        st.markdown("### 📊 Info")
        st.write("Language:", data["language"])
        st.write("ASR confidence:", data["confidence"])
