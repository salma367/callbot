import os
from fastapi import WebSocket, WebSocketDisconnect
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.utils.audio_utils import normalize_for_asr


class VoiceWSState:
    """Per-connection state."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_ai_speaking = True  # AI speaks first


async def send_mp3(ws: WebSocket, mp3_path: str):
    """Send MP3 bytes over WebSocket."""
    with open(mp3_path, "rb") as f:
        data = f.read()
    await ws.send_bytes(data)


async def ai_speak(
    ws: WebSocket, state: VoiceWSState, text: str, pipeline: VoicePipeline
):
    """Run TTS and send audio to client in French."""
    state.is_ai_speaking = True
    mp3_path = pipeline.tts.synthesize(text=text, lang="fr")
    await send_mp3(ws, mp3_path)
    state.is_ai_speaking = False
    await ws.send_json({"event": "ai_done"})


async def voice_ws_endpoint(
    ws: WebSocket,
    pipeline: VoicePipeline,
    session_manager: SessionManager,
    temp_dir: str,
):
    """
    WebSocket voice handler:
    - Sends initial greeting
    - Receives user audio
    - Processes with ASR -> NLU -> RAG -> LLM -> TTS
    - Sends AI audio back
    """
    session = session_manager.create()
    state = VoiceWSState(session.session_id)

    try:
        # 1️⃣ AI greeting in French
        greeting = "Bonjour! Je suis votre assistant vocal pour l'assurance. Quand j'aurai fini de parler, vous pouvez poser votre question."
        await ai_speak(ws, state, greeting, pipeline)
        session.log_turn("AI", greeting)

        while True:
            message = await ws.receive()

            if "bytes" not in message:
                continue

            if state.is_ai_speaking:
                continue  # ignore user input while AI speaks

            audio_bytes = message["bytes"]

            # Save temporary audio
            os.makedirs(temp_dir, exist_ok=True)
            tmp_path = os.path.join(temp_dir, f"{state.session_id}.webm")
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            # Normalize audio for ASR
            normalized_path = os.path.join(temp_dir, f"{state.session_id}_16k.wav")
            normalize_for_asr(tmp_path, normalized_path)

            # 2️⃣ Process audio
            result = pipeline.process_audio(normalized_path)

            if "error" in result:
                fallback_text = "Désolé, je n'ai pas compris. Veuillez répéter."
                await ai_speak(ws, state, fallback_text, pipeline)
                session.log_turn("AI", fallback_text)
                continue

            # 3️⃣ Log user & AI turns
            session.log_turn("User", result["text"])
            session.log_turn("AI", result["response_text"], result["audio_response"])

            # 4️⃣ Send AI audio and JSON event
            await send_mp3(ws, result["audio_response"])
            await ws.send_json({"event": "ai_done"})

    except WebSocketDisconnect:
        session_manager.clear(session.session_id)
        print(f"WebSocket disconnected: {state.session_id}")
    except Exception as e:
        session_manager.clear(session.session_id)
        print(f"Error in voice_ws_endpoint: {e}")
        await ws.close()
