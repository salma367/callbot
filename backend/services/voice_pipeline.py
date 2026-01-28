# backend/services/voice_pipeline.py

from backend.models import intent
from backend.services.asr_service import ASRService
from backend.services.tts_service import TTSService
from backend.services.nlu_service import NLUService
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.controllers.orchestrator import Orchestrator


class VoicePipeline:
    MIN_CONFIDENCE = 0.35

    def __init__(self):
        self.asr = ASRService()
        self.tts = TTSService()
        self.nlu = NLUService()
        self.llm = LLMService()
        self.rag = RAGService()
        self.orchestrator = Orchestrator()

    def process_audio(self, audio_path: str, call_session=None) -> dict:
        """Process the audio end-to-end with full debug info."""

        print(f"[DEBUG] Processing audio: {audio_path}")

        asr_result = self.asr.transcribe_voice(audio_path)
        text = asr_result.get("text", "").strip()
        language = asr_result.get("language", "unknown")
        asr_conf = asr_result.get("confidence", 0.0)
        print(
            f"[DEBUG] ASR output: '{text}' | Confidence: {asr_conf} | Language: {language}"
        )

        if not text or asr_conf < self.MIN_CONFIDENCE:
            print("[DEBUG] ASR failed or below MIN_CONFIDENCE")
            return {
                "error": "asr_failed",
                "language": language,
                "confidence": asr_conf,
            }

        detected_intent = self.nlu.detect_intent(text)
        nlu_conf = detected_intent.confidence if detected_intent else 0.0
        intent_name = detected_intent.name if detected_intent else "UNKNOWN"
        print(f"[DEBUG] Detected intent: '{intent_name}' | Confidence: {nlu_conf}")

        # 3️⃣ RAG retrieval
        contexts = self.rag.retrieve(text, k=4)
        context = "\n".join(contexts) if contexts else ""
        print(f"[DEBUG] RAG retrieved contexts: {contexts}")

        # 4️⃣ LLM response
        try:
            response_text = self.llm.generate_response(
                user_text=text,
                context=context,
                language=language,
                intent=intent_name,
            )
        except Exception as e:
            response_text = "Je suis désolé, je n'ai pas pu générer de réponse."
            print(f"[DEBUG] LLM error: {e}")
        print(f"[DEBUG] LLM response: '{response_text}'")

        # 5️⃣ TTS
        try:
            tts_audio_path = self.tts.synthesize(text=response_text, lang="fr")
            print(f"[DEBUG] TTS audio generated: {tts_audio_path}")
        except Exception as e:
            tts_audio_path = None
            print(f"[DEBUG] TTS generation failed: {e}")

        # 6️⃣ Orchestrator decision (if call_session provided)
        orchestration_result = None
        if call_session:
            turn_result = self.orchestrator.process_turn(
                call_session=call_session,
                intent=detected_intent,
                asr_conf=asr_conf,
                nlu_conf=nlu_conf,
                ambiguous=False,
            )
            orchestration_result = turn_result
            print(f"[DEBUG] Orchestrator turn result: {turn_result}")

        # 7️⃣ Return full debug info
        return {
            "text": text,
            "intent": intent_name,
            "asr_confidence": asr_conf,
            "nlu_confidence": nlu_conf,
            "response_text": response_text,
            "language": language,
            "audio_response": tts_audio_path,
            "orchestration_result": orchestration_result,
        }
