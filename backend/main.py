from fastapi import FastAPI, UploadFile, File, Form
import shutil
import os
import uuid
from backend.services.voice_pipeline import VoicePipeline
from backend.utils.audio_utils import normalize_for_asr
from backend.services.session_manager import SessionManager
from backend.services.voice_pipeline import VoicePipeline


app = FastAPI()
pipeline = VoicePipeline()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


@app.post("/call/voice")
async def voice_call(audio: UploadFile = File(...)):
    uid = uuid.uuid4().hex
    raw_path = os.path.join(TEMP_DIR, f"{uid}_raw.wav")
    norm_path = os.path.join(TEMP_DIR, f"{uid}_norm.wav")

    with open(raw_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    normalize_for_asr(raw_path, norm_path)

    result = pipeline.process_audio(norm_path)

    try:
        os.remove(raw_path)
        os.remove(norm_path)
    except Exception:
        pass

    return result


session_manager = SessionManager()
pipeline = VoicePipeline()
TEMP_DIR = "temp"


@app.post("/call/voice/stream")
async def voice_stream(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    is_final: bool = Form(False),
):
    session = session_manager.get(session_id)

    chunk_id = uuid.uuid4().hex
    chunk_path = os.path.join(TEMP_DIR, f"{session_id}_{chunk_id}.wav")

    with open(chunk_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    session.add_chunk(chunk_path)

    buffered_audio = session.get_buffered_audio()

    result = pipeline.process_audio(buffered_audio)

    if is_final:
        session_manager.clear(session_id)

    return {
        "partial_text": result["text"],
        "confidence": result["confidence"],
        "is_final": is_final,
    }
