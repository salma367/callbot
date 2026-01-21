from fastapi import FastAPI, UploadFile, File
import shutil
import os

from backend.services.voice_pipeline import VoicePipeline
from backend.utils.audio_utils import normalize_for_asr

app = FastAPI()
pipeline = VoicePipeline()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/call/voice")
async def voice_call(audio: UploadFile = File(...)):
    raw_path = os.path.join(TEMP_DIR, audio.filename)
    norm_path = os.path.join(TEMP_DIR, f"norm_{audio.filename}.wav")

    with open(raw_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    normalize_for_asr(raw_path, norm_path)

    result = pipeline.process_audio(norm_path)

    return result
