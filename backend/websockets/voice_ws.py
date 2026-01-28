import os
import json
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.utils.audio_utils import normalize_for_asr
from backend.models.call_session import CallSession
from backend.models.intent import Intent
from backend.controllers.CallReport import CallReport
from backend.controllers.orchestrator import Orchestrator

orchestrator = Orchestrator()


class VoiceWSState:
    """Per-connection WebSocket state."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_ai_speaking = True


async def send_mp3(ws: WebSocket, mp3_path: str):
    """Send MP3 bytes over WebSocket safely."""
    if not mp3_path or not os.path.exists(mp3_path):
        print(f"[TTS WARNING] File not found: {mp3_path}")
        return
    try:
        with open(mp3_path, "rb") as f:
            await ws.send_bytes(f.read())
    except Exception as e:
        print(f"[TTS ERROR] Failed to send MP3: {e}")


async def ai_speak(
    ws: WebSocket, state: VoiceWSState, text: str, pipeline: VoicePipeline
):
    """Run TTS and send audio to client in French."""
    state.is_ai_speaking = True
    try:
        mp3_path = pipeline.tts.synthesize(text=text, lang="fr")
        await send_mp3(ws, mp3_path)
    except Exception as e:
        print(f"[TTS ERROR] Could not synthesize TTS: {e}")
        mp3_path = None
    finally:
        state.is_ai_speaking = False
        await ws.send_json({"event": "ai_done"})


async def voice_ws_endpoint(
    ws: WebSocket,
    pipeline: VoicePipeline,
    session_manager: SessionManager,
    temp_dir: str,
):
    await ws.accept()
    session: CallSession = session_manager.create()
    state = VoiceWSState(session.call_id)

    try:
        # --- Initial greeting ---
        greeting = "Bonjour ! Je suis votre assistant vocal pour l'assurance."
        await ai_speak(ws, state, greeting, pipeline)
        session.add_message(greeting)

        while True:
            try:
                message = await ws.receive()
            except WebSocketDisconnect:
                print(f"[WS] Disconnected: {state.session_id}")
                break
            except RuntimeError as e:
                if "Cannot call" in str(e) and "disconnect" in str(e):
                    print(f"[WS] Connection already closed: {state.session_id}")
                    break  # Exit the loop
                else:
                    raise

            # --- JSON control messages ---
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                except Exception:
                    continue

                if payload.get("event") == "end_call":
                    session.end()
                    report = CallReport(session)
                    report.final_decision = session.final_decision
                    report.average_confidence = session.get_average_confidence()
                    report.generateSummary()
                    print("[CALL REPORT]", report.summary_text)
                    break  # cleanly exit loop

                continue

            # --- Binary audio ---
            if "bytes" not in message or state.is_ai_speaking:
                continue

            audio_bytes = message["bytes"]
            os.makedirs(temp_dir, exist_ok=True)
            tmp_path = os.path.join(temp_dir, f"{session.call_id}.webm")
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            normalized_path = os.path.join(temp_dir, f"{session.call_id}_16k.wav")
            normalize_for_asr(tmp_path, normalized_path)

            # --- Voice pipeline ---
            result = pipeline.process_audio(normalized_path)
            print(f"[DEBUG WS] ASR/NLU result: {result}")
            if "error" in result:
                fallback = "Désolé, je n'ai pas compris. Pouvez-vous répéter ?"
                await ai_speak(ws, state, fallback, pipeline)
                session.add_message(fallback)
                continue

            # --- Log user text ---
            user_text = result.get("text", "")
            session.add_message(user_text)
            asr_conf = result.get("confidence", 0.8)
            nlu_conf = result.get("nlu_confidence", 0.8)

            # --- Ensure intent object ---
            intent_obj = result.get("intent")
            if isinstance(intent_obj, str):
                intent_obj = Intent(name=intent_obj.upper(), confidence=nlu_conf)
            elif intent_obj is None:
                intent_obj = Intent(name="UNKNOWN", confidence=0.2)

            # --- Orchestrator decision ---
            turn_result = orchestrator.process_turn(
                call_session=session,
                intent=intent_obj,
                asr_conf=asr_conf,
                nlu_conf=nlu_conf,
                ambiguous=False,
            )
            print(f"[DEBUG WS] Orchestrator turn_result: {turn_result}")

            # --- CRITICAL FIX: Add session_id to turn_result ---
            turn_result["call_id"] = session.call_id

            # --- Send JSON first (important!) ---
            print(f"[DEBUG WS] Sending JSON to client: {turn_result}")
            await ws.send_json(turn_result)

            # --- Check if we need to escalate (stop audio) ---
            if turn_result.get("decision") == "AGENT":
                # Don't send audio for escalations
                print(f"[DEBUG WS] Escalation detected, skipping audio")
                # Wait a bit for frontend to process escalation
                await asyncio.sleep(0.1)
                continue

            # --- Send AI audio safely ---
            ai_audio_path = turn_result.get("audio_response") or result.get(
                "audio_response"
            )
            if ai_audio_path and os.path.exists(ai_audio_path):
                print(f"[DEBUG WS] Sending TTS audio: {ai_audio_path}")
                await send_mp3(ws, ai_audio_path)
                # Send ai_done event after audio
                await ws.send_json({"event": "ai_done"})

    finally:
        session_manager.clear(session.call_id)
        if ws.client_state.name != "DISCONNECTED":
            try:
                await ws.close()
            except Exception:
                pass
