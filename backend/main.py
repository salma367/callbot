import os
import uvicorn
from fastapi import FastAPI, WebSocket, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
from contextlib import asynccontextmanager

from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.services.llm_service import LLMService
from backend.controllers.orchestrator import Orchestrator
from backend.models.call_report import CallReport
from backend.controllers.CallProcessRequest import CallProcessRequest
from backend.repositories.client_repo import get_or_create_client
from backend.websockets.voice_ws import voice_ws_endpoint


# ═══════════════════════════════════════════════════════════
# LIFECYCLE MANAGEMENT
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print("[STARTUP] Initializing services...")

    # Pre-warm models to avoid first-call latency
    try:
        print("[STARTUP] Warming up ASR...")
        # Create dummy audio file if needed for warmup
        # app.state.pipeline.asr.transcribe_voice("path/to/dummy.wav")

        print("[STARTUP] Warming up NLU...")
        app.state.pipeline.nlu.detect_intent("Bonjour")

        print("[STARTUP] Warming up LLM...")
        app.state.llm_service.generate_response("Test", "", "fr", "GREETING")

        print("[STARTUP] Services ready!")
    except Exception as e:
        print(f"[STARTUP] Warmup failed (non-critical): {e}")

    yield

    # Shutdown
    print("[SHUTDOWN] Cleaning up...")
    # Cleanup temp files, close connections, etc.
    try:
        import shutil

        if os.path.exists("temp"):
            shutil.rmtree("temp")
    except Exception as e:
        print(f"[SHUTDOWN] Cleanup error: {e}")


# ═══════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="Callbot AI",
    description="AI-first voice callbot for insurance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Replace with specific origins in production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ═══════════════════════════════════════════════════════════
# GLOBAL STATE (attached to app for cleaner access)
# ═══════════════════════════════════════════════════════════
app.state.pipeline = VoicePipeline()
app.state.session_manager = SessionManager()
app.state.llm_service = LLMService()
app.state.orchestrator = Orchestrator(llm_service=app.state.llm_service)
app.state.active_calls = {}  # In-memory session store


# ═══════════════════════════════════════════════════════════
# REST API ROUTES
# ═══════════════════════════════════════════════════════════
router = APIRouter(prefix="/call", tags=["Call Management"])


@router.get("/start")
def start_call(
    user_name: str = Query("FrontEnd User", description="Full name of the user"),
    phone_number: str = Query("000000000", description="Phone number of the user"),
):
    """
    Start a new call session.
    Returns call_id and client_id.
    """
    try:
        # Validate and get/create client
        client_id = get_or_create_client(full_name=user_name, phone_number=phone_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create session
    call_session = app.state.session_manager.create(
        user_name=user_name,
        phone_number=phone_number,
    )

    # Initialize orchestrator
    app.state.orchestrator.on_call_started(call_session)

    # Store in active calls
    app.state.active_calls[call_session.call_id] = call_session

    return {
        "call_id": call_session.call_id,
        "message": "Call started successfully",
        "phone_number": call_session.phone_number,
        "client_id": call_session.client_id,
    }


@router.post("/process")
def process_call(request: CallProcessRequest):
    """
    Process a turn in an ongoing call session.
    (Legacy endpoint - WebSocket is preferred)
    """
    call_session = app.state.active_calls.get(request.call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Mock confidences (in real scenario, these come from ASR/NLU)
    asr_conf = 0.9
    nlu_conf = 0.8

    response = app.state.orchestrator.process_turn(
        call_session=call_session,
        intent=None,  # TODO: Replace with actual Intent object
        asr_conf=asr_conf,
        nlu_conf=nlu_conf,
    )

    return {
        "call_session": Orchestrator.serialize_call_session(call_session),
        "response": response,
    }


@router.get("/end")
def end_call(call_id: str = Query(..., description="Call session ID")):
    """
    End a call session and generate a summary report.
    """
    call_session = app.state.active_calls.get(call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # End session
    call_session.end_call(status="COMPLETED")

    # Compute average confidence
    avg_conf = (
        call_session.get_average_confidence()
        if hasattr(call_session, "get_average_confidence")
        else 0.0
    )
    call_session.average_confidence = avg_conf

    # Generate report
    report = CallReport(call_session)
    report.final_decision = getattr(call_session, "final_decision", "UNKNOWN")
    report.average_confidence = avg_conf

    try:
        summary = report.generate_summary(llm_service=app.state.llm_service)
    except Exception as e:
        print(f"[REPORT] Summary generation failed: {e}")
        summary = "Summary generation failed."

    # Remove from active calls
    app.state.active_calls.pop(call_id, None)

    return {
        "call_session": Orchestrator.serialize_call_session(call_session),
        "summary": summary,
        "user_name": getattr(call_session, "user_name", "Unknown"),
        "phone_number": getattr(call_session, "phone_number", "Unknown"),
        "client_id": getattr(call_session, "client_id", "Unknown"),
    }


@router.get("/active")
def list_active_calls():
    """List all active call sessions."""
    return {
        "active_calls": list(app.state.active_calls.keys()),
        "count": len(app.state.active_calls),
    }


# Include router
app.include_router(router)


# ═══════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT (primary interface)
# ═══════════════════════════════════════════════════════════
@app.websocket("/ws/voice")
async def websocket_endpoint(ws: WebSocket):
    """Real-time voice interaction via WebSocket."""
    await voice_ws_endpoint(
        ws=ws,
        pipeline=app.state.pipeline,
        session_manager=app.state.session_manager,
        temp_dir="temp",
    )


# ═══════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════
@app.get("/health")
def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "asr": "ok",
            "nlu": "ok",
            "llm": "ok",
            "tts": "ok",
        },
        "active_sessions": len(app.state.active_calls),
    }


# ═══════════════════════════════════════════════════════════
# START SERVER
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(
        """

    ║  WebSocket: ws://localhost:8000/ws/voice             ║
    ║  REST API:  http://localhost:8000/call/*             ║
    ║  Health:    http://localhost:8000/health             ║
    ║  Docs:      http://localhost:8000/docs               ║

    """
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
