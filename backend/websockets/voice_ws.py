import os
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from backend.utils.audio_utils import is_silent_wav, normalize_for_asr
from backend.services.voice_pipeline import VoicePipeline
from backend.services.session_manager import SessionManager
from backend.models.call_session import CallSession
from backend.models.intent import Intent
from backend.models.call_report import CallReport
from backend.controllers.orchestrator import Orchestrator
from backend.services.llm_service import LLMService
from backend.controllers.callbot_controller import finalize_call

llm_service = LLMService()
orchestrator = Orchestrator(llm_service=llm_service)


class VoiceWSState:
    """Per-connection WebSocket state."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_ai_speaking = True


async def send_mp3(ws: WebSocket, mp3_path: str):
    if not mp3_path or not os.path.exists(mp3_path):
        print(f"[AUDIO][WARN] MP3 not found: {mp3_path}")
        return
    try:
        with open(mp3_path, "rb") as f:
            await ws.send_bytes(f.read())
    except Exception as e:
        print(f"[AUDIO][ERROR] Failed to send MP3: {e}")


async def ai_speak(
    ws: WebSocket, state: VoiceWSState, text: str, pipeline: VoicePipeline
):
    state.is_ai_speaking = True
    try:
        mp3_path = pipeline.tts.synthesize(text=text, lang="fr")
        await send_mp3(ws, mp3_path)
    except Exception as e:
        print(f"[TTS][ERROR] {e}")
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
    session = None
    state = None
    user_name = "FrontEnd User"
    phone_number = "000000000"

    # --- Wait for client registration ---
    while session is None:
        try:
            message = await ws.receive()
        except WebSocketDisconnect:
            print("[WS] Client disconnected before registration")
            return

        if "text" in message:
            try:
                payload = json.loads(message["text"])
            except Exception:
                continue

            if payload.get("event") == "register_client":
                user_name = payload.get("user_name", "FrontEnd User")
                phone_number = payload.get("phone_number", "000000000")

                # --- Create call session (SessionManager handles client_id internally) ---
                session = session_manager.create(
                    user_name=user_name,
                    phone_number=phone_number,
                )
                state = VoiceWSState(session.call_id)
                print(f"[WS] Connection accepted | call_id={session.call_id}")
                break

    try:
        # --- Initial greeting ---
        greeting = "Bonjour ! Je suis votre assistant vocal pour l'assurance."
        await ai_speak(ws, state, greeting, pipeline)
        session.add_message(greeting)

        while True:
            try:
                message = await ws.receive()
            except WebSocketDisconnect:
                print(f"[WS] Client disconnected | call_id={session.call_id}")
                break
            except RuntimeError as e:
                if "disconnect" in str(e):
                    print(f"[WS] Runtime disconnect | call_id={session.call_id}")
                    break
                raise

            # --- Handle text control messages ---
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                except Exception:
                    continue

                if payload.get("event") == "end_call":
                    print(f"[SESSION] End call requested | call_id={session.call_id}")
                    session.end_call(status="RESOLVED")
                    finalize_call(session)
                    break
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

            if is_silent_wav(normalized_path):
                continue

            # --- Process audio ---
            result = pipeline.process_audio(normalized_path)
            if "error" in result:
                fallback = "Désolé, je n'ai pas compris. Pouvez-vous répéter ?"
                await ai_speak(ws, state, fallback, pipeline)
                session.add_message(fallback)
                continue

            user_text = result.get("text", "")
            session.add_message(user_text)
            asr_conf = result.get("asr_confidence", 0.8)
            nlu_conf = result.get("nlu_confidence", 0.8)

            intent_obj = result.get("intent")
            if isinstance(intent_obj, str):
                intent_obj = Intent(name=intent_obj.upper(), confidence=nlu_conf)
            elif intent_obj is None:
                intent_obj = Intent(name="UNKNOWN", confidence=0.2)

            turn_result = orchestrator.process_turn(
                call_session=session,
                intent=intent_obj,
                asr_conf=asr_conf,
                nlu_conf=nlu_conf,
                ambiguous=False,
            )
            turn_result["call_id"] = session.call_id
            await ws.send_json(turn_result)

            # 🔚 Call end handling (GOODBYE)
            if turn_result.get("reason") == "USER_GOODBYE":
                print(f"[WS] Call ended by goodbye | call_id={session.call_id}")
                session.end_call(status="ENDED")
                finalize_call(session)
                break

            # --- Escalation handling ---
            if turn_result.get("decision") == "AGENT":
                print("[WS] Escalation detected -> ending call")
                session.end_call(status="ESCALATED")
                finalize_call(session)
                await asyncio.sleep(0.1)
                continue

            # --- Send AI audio ---
            ai_text = (
                turn_result.get("message")
                or turn_result.get("response")
                or result.get("response_text")
            )
            if ai_text:
                await ai_speak(ws, state, ai_text, pipeline)

    finally:
        print(f"[SESSION] Cleaning up | call_id={session.call_id}")
        session_manager.clear(session.call_id)
        if ws.client_state.name != "DISCONNECTED":
            try:
                await ws.close()
            except Exception:
                pass
