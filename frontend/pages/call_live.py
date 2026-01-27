import streamlit as st
import requests
from audiorecorder import audiorecorder
import tempfile
import os
from io import BytesIO

st.set_page_config(page_title="Voice Call", layout="centered")

# -----------------------------
# Call state
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "call_active" not in st.session_state:
    st.session_state.call_active = False
if "ai_turn" not in st.session_state:
    st.session_state.ai_turn = False
if "user_turn_ready" not in st.session_state:
    st.session_state.user_turn_ready = False

st.title("Live Voice Call")

# -----------------------------
# Start / End buttons
# -----------------------------
col1, col2 = st.columns(2)
with col1:
    start_btn = st.button("Start Call")
with col2:
    end_btn = st.button("End Call")

# -----------------------------
# Start Call
# -----------------------------
if start_btn and not st.session_state.call_active:
    res = requests.post("http://localhost:8000/call/voice/start")
    if res.ok:
        data = res.json()
        st.session_state.session_id = data["session_id"]
        st.session_state.call_active = True
        st.session_state.ai_turn = True
        st.session_state.user_turn_ready = False

        st.markdown(
            "<div class='card'><b>AI is speaking...</b></div>", unsafe_allow_html=True
        )
        st.audio(data["audio_response"], format="audio/wav")
        st.markdown(
            f"<div class='card'><b>AI says:</b> {data['text']}</div>",
            unsafe_allow_html=True,
        )

# -----------------------------
# End Call
# -----------------------------
if end_btn and st.session_state.call_active:
    requests.post(
        "http://localhost:8000/call/voice/end",
        data={"session_id": st.session_state.session_id},
    )
    st.session_state.session_id = None
    st.session_state.call_active = False
    st.session_state.ai_turn = False
    st.session_state.user_turn_ready = False
    st.success("Call ended.")

# -----------------------------
# AI Turn
# -----------------------------
if st.session_state.call_active and st.session_state.ai_turn:
    st.markdown(
        "<div class='card'><b>AI just spoke. Wait for your turn...</b></div>",
        unsafe_allow_html=True,
    )
    # AI has finished → now user can speak
    st.session_state.ai_turn = False
    st.session_state.user_turn_ready = True

# -----------------------------
# User Turn
# -----------------------------
if st.session_state.call_active and st.session_state.user_turn_ready:
    st.markdown(
        "<div class='card'><b>Your turn to speak...</b></div>", unsafe_allow_html=True
    )

    audio_segment = audiorecorder("Start recording", "Stop recording")
    uploaded_audio = st.file_uploader("Or upload audio", type=["wav", "mp3"])

    audio_file_path = None

    def audiosegment_to_wav_bytes(audio_segment):
        buf = BytesIO()
        audio_segment.export(buf, format="wav")
        return buf.getvalue()

    if len(audio_segment) > 0:
        wav_bytes = audiosegment_to_wav_bytes(audio_segment)
        st.audio(wav_bytes, format="audio/wav")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(wav_bytes)
            audio_file_path = f.name
    elif uploaded_audio is not None:
        audio_file_path = uploaded_audio

    if audio_file_path and st.button("Send Audio"):
        with open(audio_file_path, "rb") as f:
            files = {"audio": f}
            data = {"session_id": st.session_state.session_id}
            res = requests.post(
                "http://localhost:8000/call/voice/stream", files=files, data=data
            )

        if res.ok:
            result = res.json()
            st.markdown(
                "<div class='card'><b>AI is speaking...</b></div>",
                unsafe_allow_html=True,
            )
            st.audio(result["audio_response"], format="audio/wav")
            st.markdown(
                f"<div class='card'><b>AI says:</b> {result['response_text']}</div>",
                unsafe_allow_html=True,
            )

            # Prepare next turn
            st.session_state.ai_turn = True
            st.session_state.user_turn_ready = False

        # Cleanup temp file
        if isinstance(audio_file_path, str) and os.path.exists(audio_file_path):
            os.remove(audio_file_path)
