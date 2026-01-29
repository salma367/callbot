import os
from backend.services.llm_service import LLMService
import uvicorn
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.controllers.orchestrator import Orchestrator
from backend.models.call_report import CallReport
from backend.controllers.CallProcessRequest import CallProcessRequest
from fastapi import APIRouter
from backend.repositories.client_repo import get_or_create_client

# ---------- FastAPI app ----------
app = FastAPI(title="Callbot AI")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Global objects ----------
pipeline = VoicePipeline()
session_manager = SessionManager()
llm_service = LLMService()
orchestrator = Orchestrator(llm_service=llm_service)
active_calls = {}

# ---------- REST ROUTES ----------
router = APIRouter(prefix="/call", tags=["Call"])


@router.get("/start")
def start_call(
    user_name: str | None = Query(None, description="Full name of the user"),
    phone_number: str | None = Query(None, description="Phone number of the user"),
):
    """
    Start a new call session.
    Throws an error if the phone number exists with a different name.
    """
    user_name = user_name or "FrontEnd User"
    phone_number = phone_number or "000000000"

    try:
        # This handles both: checking for name mismatch and creating/retrieving client
        client_id = get_or_create_client(full_name=user_name, phone_number=phone_number)
    except ValueError:
        return {"error": "Le numéro est déjà associé à un autre utilisateur."}

    # Create session
    call_session = session_manager.create(
        user_name=user_name,
        phone_number=phone_number,
    )

    orchestrator.on_call_started(call_session)
    active_calls[call_session.call_id] = call_session

    return {
        "call_id": call_session.call_id,
        "message": "Call started",
        "phone_number": call_session.phone_number,
        "client_id": call_session.client_id,
    }


@router.post("/process")
def process_call(request: CallProcessRequest):
    """
    Process a turn in an ongoing call session.
    """
    call_session = active_calls.get(request.call_id)
    if not call_session:
        return {"error": "Call session not found"}

    # Example: ASR/NLU confidence (in a real setup, you'd get this from ASR/NLU)
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
    """
    End a call session and generate a call report.
    """
    call_session = active_calls.get(call_id)
    if not call_session:
        return {"error": "Call session not found"}

    call_session.end()

    # Compute average confidence
    avg_conf = call_session.get_average_confidence()
    call_session.average_confidence = avg_conf

    # Generate report
    report = CallReport(call_session)
    report.final_decision = getattr(call_session, "final_decision", "UNKNOWN")
    report.average_confidence = avg_conf
    summary = report.generate_summary(llm_service=llm_service)

    # Remove session from active calls
    active_calls.pop(call_id, None)

    return {
        "call_session": Orchestrator.serialize_call_session(call_session),
        "summary": summary,
        "user_name": getattr(call_session, "user_name", "Unknown"),
        "phone_number": getattr(call_session, "phone_number", "Unknown"),
        "client_id": getattr(call_session, "client_id", "Unknown"),
    }


# Include router
app.include_router(router)

# ---------- WebSocket ----------
from backend.websockets.voice_ws import voice_ws_endpoint


@app.websocket("/ws/voice")
async def websocket_endpoint(ws: WebSocket):
    await voice_ws_endpoint(
        ws=ws, pipeline=pipeline, session_manager=session_manager, temp_dir="temp"
    )


# ---------- START SERVER ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
