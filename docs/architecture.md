# Architecture Overview

This document describes the high-level architecture of the Callbot project, how components interact, and where to look in the codebase for each responsibility. The goal is to provide a practical, readable overview for developers who want to run, extend, or debug the system.

## Summary

The system is an AI-driven voice call assistant designed for insurance scenarios. Incoming voice is processed through an audio pipeline that converts speech to text, extracts intent, optionally augments with retrieved knowledge, generates a text response using an LLM, and returns speech using a TTS service. The architecture separates concerns into backend services, controllers, models, and a lightweight frontend for demo and testing.

## High-level components

- Backend services: audio processing, NLU, LLM, RAG, TTS, session management, orchestration, and support services (confidence, escalation, logging).
- Controllers / API: HTTP endpoints and WebSocket handlers for the voice stream and control flows.
- Models & repositories: in-memory and persistent representations of calls, clients, and call reports.
- Frontend: simple web UI and demo pages used to interact with the callbot for manual testing.
- Vector store: a Chroma-backed vector database for RAG (FAQ/context retrieval).

## Backend (where to look)

- `backend/services/voice_pipeline.py` – central pipeline that orchestrates ASR → NLU → RAG → LLM → TTS and returns structured results. This is the primary entry point for processing audio input.
- `backend/services/asr_service.py` – speech-to-text using Faster Whisper (faster-whisper). Produces transcript and confidence.
- `backend/services/nlu_service.py` – intent detection and lightweight pattern rules; falls back to LLM classification when needed.
- `backend/services/rag_service.py` – retrieves relevant FAQ or knowledge documents from a Chroma vectorstore using sentence-transformers embeddings.
- `backend/services/llm_service.py` – builds system/user prompts and calls the configured LLM API (requires environment keys).
- `backend/services/tts_service.py` – text-to-speech with ElevenLabs first and gTTS as fallback; includes caching of generated audio.
- `backend/services/session_manager.py` and `backend/models/call_session.py` – manage call lifecycle and message history.
- `backend/controllers/orchestrator.py` – business logic that decides whether to answer, ask for clarification, or escalate to a human agent.
- `backend/controllers/callbot_controller.py` and `backend/websockets/voice_ws.py` – HTTP/WebSocket endpoints that integrate with the frontend and handle real-time audio streams.

## Frontend

The frontend is intentionally minimal and intended for demonstrations and manual testing. Key files:

- `frontend/callbot/index.html` and `frontend/callbot/voice.js` – the browser UI that captures microphone audio and communicates with the WebSocket endpoint.
- `frontend/dashboard/*` – a small dashboard for viewing call summaries and reports.

## Data and persistence

- Vector store: `backend/vectorstore/chroma` (Chroma persistent client) stores embeddings and documents for RAG.
- Call reports and other artifacts are saved via repository modules in `backend/repositories/` — these are lightweight and designed to be adaptable to a real database.
- Generated TTS outputs are cached under `demo/tts_outputs` to avoid re-generating the same audio repeatedly.

## External integrations

- LLM provider: configured via environment variables (GROQ_API_KEY in this project). See `backend/services/llm_service.py`.
- TTS: ElevenLabs when an API key is available, otherwise gTTS is used as a fallback. See `backend/services/tts_service.py`.
- ASR: faster-whisper model loaded in `backend/services/asr_service.py`.
- Embeddings: sentence-transformers for embedding FAQ text for Chroma.

## Runtime & lifecycle

- The FastAPI application is defined in `backend/main.py`. It sets up `app.state` with pre-created service instances (pipeline, LLM, orchestrator) so components can be reused across requests.
- Startup warmup calls (ASR, NLU, LLM) are executed to reduce first-call latency.
- For local testing, `test2.py` and `gen_transfer_audio.py` provide CLI flows for running the pipeline without the browser UI or for creating a single TTS audio file.

## Observability and logging

- Logging is handled by `backend/logs/logger.py`. Significant events such as call start/end, orchestration decisions, and LLM errors are logged for debugging.

## Security and configuration

- API keys and secrets are read from environment variables (handled with `python-dotenv` in service modules). Do not commit sensitive keys to source control.
- The system treats sensitive intents specially and contains an escalation policy; any integration with production PII or payment flows must add explicit security controls and audit logging.

## Extensibility and where to change behavior

- To change intent definitions or pattern rules, edit `backend/services/nlu_service.py`.
- To customize response behavior and safety rules, adjust the prompts and templates in `backend/services/llm_service.py`.
- Orchestration logic (when to escalate or clarifiy) lives in `backend/controllers/orchestrator.py`.
- To add new retrieval sources (database, knowledge base), extend `backend/services/rag_service.py` or add a new retrieval module used by the pipeline.

## Running locally (quick start)

1. Create and activate a Python 3.10 virtual environment.
2. Install dependencies from `requirements.txt`.
3. Set required environment variables (at least `GROQ_API_KEY` for LLM). Optionally set `ELEVENLABS_API_KEY` for ElevenLabs TTS.

Example commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY="your_key_here"
export ELEVENLABS_API_KEY="your_key_here"  
python backend/main.py  
```

For quick CLI testing without the UI:

```bash
cd demo
python Console_demo.py    
```

## Notes and caveats

- Some services expect API keys and will raise errors if keys are missing (LLM and optional ElevenLabs). The code includes fallbacks where feasible (gTTS fallback for TTS).
- The project currently uses a local Chroma store under `backend/vectorstore/chroma`; ensure the embedding model and Chroma are available when using RAG.

