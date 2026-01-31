# Callbot & Dashboard

A local call center prototype that includes a dashboard and an AI callbot. The project is intended for development and testing; it demonstrates how to capture audio from a browser, process it with ASR and NLU, generate responses with an LLM, and return speech with a TTS engine.

## Components

- `Backend API` — provides call data used by the dashboard.
- `Backend Callbot` — the AI pipeline (ASR → NLU → RAG → LLM → TTS), session management, orchestration, and report generation.
- `Frontend Dashboard` — a simple web UI for agents to view call summaries and reports.
- `Frontend Callbot` — a minimal browser client used to simulate calls and stream audio to the backend.

## Prerequisites

- Python 3.10 (use a virtual environment)
- A working internet connection for optional external APIs (LLM, ElevenLabs)

Recommended: run inside a virtual environment to keep dependencies isolated.

## Quick setup

Clone and install:

```bash
git clone <repo-url>
cd callbot
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

The project uses environment variables for external API keys. Create a `.env` file in the repository root or export the variables in your shell:

```bash
export GROQ_API_KEY="your_groq_api_key"
export ELEVENLABS_API_KEY="your_elevenlabs_key"  # optional (TTS)
```

Notes:
- `GROQ_API_KEY` is required for the LLM service used in this project. Without it the LLM service will raise an error.
- `ELEVENLABS_API_KEY` is optional. If missing, the project falls back to `gTTS` for TTS output.

## Running the system

Backend API (call data):

```bash
source .venv/bin/activate
python backend/api.py
```

Backend Callbot (FastAPI, AI pipeline):

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload
```

Frontends (static servers for local testing):

```bash
source .venv/bin/activate
cd frontend/dashboard
python -m http.server 8005

cd ../callbot
python -m http.server 8002
```

Open the dashboard at http://127.0.0.1:8005 and the callbot UI at http://127.0.0.1:8002.

## CLI utilities for testing

- `Console_demo.py` — interactive CLI to feed text inputs and exercise the AI pipeline without the browser UI. Useful for debugging intent detection, LLM responses, and orchestration decisions.

Run them like this:

```bash
cd demo
python Console_demo.py          
```

## Data and storage

- Vector store for RAG: `backend/vectorstore/chroma` (Chroma persistent client). Embeddings are created with `sentence-transformers`.
- Generated TTS files and cache: `demo/tts_outputs`.
- Lightweight repositories are in `backend/repositories/`; they are designed for prototyping and can be replaced with a production DB.

## Notes and troubleshooting

- If the LLM raises environment errors, verify that `GROQ_API_KEY` is set.
- If TTS falls back to `gTTS`, make sure `gTTS` dependencies are installed and that the environment can play or save audio files.
- Chroma and embeddings require the model for `sentence-transformers`. If retrieval returns empty results, ensure the vectorstore is populated.

## Development tips

- Configuration and prompt templates are in `backend/services/llm_service.py`.
- Intent rules and fast-path patterns are in `backend/services/nlu_service.py`.
- Orchestration and escalation logic are in `backend/controllers/orchestrator.py`.
- To reduce first-request latency, the app warmup in `backend/main.py` calls NLU and LLM on startup.

## Ports used

- Backend API: 5000
- Frontend Dashboard: 8005
- Frontend Callbot: 8002
- Backend Callbot (FastAPI/uvicorn): 8000
