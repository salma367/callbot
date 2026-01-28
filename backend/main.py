# backend/main.py
import os
from backend.services.llm_service import LLMService
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.controllers.orchestrator import Orchestrator
from backend.models.call_report import CallReport
from backend.controllers.CallProcessRequest import CallProcessRequest
from fastapi import APIRouter

# Create FastAPI app
app = FastAPI(title="Callbot AI")

# CORS for frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global objects
pipeline = VoicePipeline()
session_manager = SessionManager()
llm_service = LLMService()
orchestrator = Orchestrator(llm_service=llm_service)
active_calls = {}

# ---------- REST ROUTES ----------

router = APIRouter(prefix="/call", tags=["Call"])


@router.get("/start")
def start_call(client_id: str | None = None):
    call_session = session_manager.create(client_id)
    orchestrator.on_call_started(call_session)
    active_calls[call_session.call_id] = call_session
    return {"call_id": call_session.call_id, "message": "Call started"}


@router.post("/process")
def process_call(request: CallProcessRequest):
    call_session = active_calls.get(request.call_id)
    if not call_session:
        return {"error": "Call session not found"}

    # Example: ASR/NLU confidence (in a real setup you get these from ASR/NLU)
    asr_conf = 0.9
    nlu_conf = 0.8

    response = orchestrator.process_turn2(
        call_session,
        intent=None,  # replace with actual Intent object
        asr_conf=asr_conf,
        nlu_conf=nlu_conf,
    )

    return {
        "call_session": Orchestrator.serialize_call_session(call_session),
        "response": response,
    }


@router.get("/end")
def end_call(call_id: str):
    call_session = active_calls.get(call_id)
    if not call_session:
        return {"error": "Call session not found"}

    call_session.end()
    # Compute average confidence
    avg_conf = call_session.get_average_confidence()
    call_session.average_confidence = avg_conf
    report = CallReport(call_session)
    report.final_decision = call_session.final_decision
    report.average_confidence = avg_conf
    summary = report.generateSummary()
    # Remove session from active calls
    active_calls.pop(call_id, None)

    return {
        "call_session": Orchestrator.serialize_call_session(call_session),
        "summary": summary,
    }


app.include_router(router)

# ---------- WebSocket ROUTE ----------

from fastapi import WebSocketDisconnect
from backend.websockets.voice_ws import voice_ws_endpoint


@app.websocket("/ws/voice")
async def websocket_endpoint(ws: WebSocket):
    await voice_ws_endpoint(
        ws=ws, pipeline=pipeline, session_manager=session_manager, temp_dir="temp"
    )


# ---------- START SERVER ----------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
