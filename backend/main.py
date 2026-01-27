from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from dotenv import load_dotenv
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.utils.audio_utils import normalize_for_asr
from backend.websockets.voice_ws import voice_ws_endpoint  # make sure this exists

# ---------------------- App & Globals ----------------------
app = FastAPI()
load_dotenv()
# Allow frontend on different port to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001"],  # frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

pipeline = VoicePipeline()  # global models load once
session_manager = SessionManager()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


# ---------------------- HTTP Endpoints ----------------------
@app.post("/call/voice/start")
def start_call():
    session = session_manager.create()
    greeting_text = (
        "Salut je suis votre assistant vocal. "
        "Quand j'ai fini de parler, vous pouvez parler."
    )
    tts_audio = pipeline.tts.synthesize(text=greeting_text, lang="fr")
    session.log_turn("AI", greeting_text, tts_audio)
    return {
        "session_id": session.session_id,
        "text": greeting_text,
        "audio_response": tts_audio,
        "is_ai_turn": True,
    }


@app.post("/call/voice/stream")
def voice_stream(session_id: str = Form(...), audio: UploadFile = File(...)):
    session = session_manager.get(session_id)
    if not session:
        return {"error": "invalid_session"}

    temp_file = os.path.join(TEMP_DIR, f"{session_id}_{audio.filename}")
    with open(temp_file, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    normalize_for_asr(temp_file, temp_file)  # optional

    result = pipeline.process_audio(temp_file)
    session.log_turn("User", result["text"])
    session.log_turn("AI", result["response_text"], result["audio_response"])

    return {
        "text": result["text"],
        "response_text": result["response_text"],
        "audio_response": result["audio_response"],
        "is_ai_turn": True,
    }


@app.post("/call/voice/end")
def end_call(session_id: str = Form(...)):
    session_manager.clear(session_id)
    return {"status": "ended"}


# ---------------------- WebSocket Endpoint ----------------------
@app.websocket("/ws/voice")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        await voice_ws_endpoint(ws, pipeline, session_manager, TEMP_DIR)
    except WebSocketDisconnect:
        print("Client disconnected")
