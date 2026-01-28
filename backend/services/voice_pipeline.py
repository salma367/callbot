# backend/services/voice_pipeline.py

from backend.services.asr_service import ASRService
from backend.services.nlu_service import NLUService
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.services.tts_service import TTSService
from backend.controllers.orchestrator import Orchestrator


class VoicePipeline:
    MIN_CONFIDENCE = 0.35

    def __init__(self):
        self.asr = ASRService()
        self.nlu = NLUService()
        self.llm = LLMService()
        self.rag = RAGService()
        self.tts = TTSService()
        self.llm_service = LLMService()
        self.orchestrator = Orchestrator(llm_service=self.llm_service)

    def process_audio(self, audio_path: str, call_session=None) -> dict:
        """Process audio → text → intent → response (NO TTS here)."""

        print(f"[DEBUG] Processing audio: {audio_path}")

        # 1️⃣ ASR
        asr_result = self.asr.transcribe_voice(audio_path)
        text = asr_result.get("text", "").strip()
        language = asr_result.get("language", "unknown")
        asr_conf = asr_result.get("confidence", 0.0)

        print(
            f"[DEBUG] ASR output: '{text}' | "
            f"Confidence: {asr_conf} | Language: {language}"
        )

        if not text or asr_conf < self.MIN_CONFIDENCE:
            print("[DEBUG] ASR failed or below MIN_CONFIDENCE")
            return {
                "error": "asr_failed",
                "language": language,
                "confidence": asr_conf,
            }

        # 2️⃣ NLU
        detected_intent = self.nlu.detect_intent(text)
        nlu_conf = detected_intent.confidence if detected_intent else 0.0
        intent_name = detected_intent.name if detected_intent else "UNKNOWN"

        print(f"[DEBUG] Detected intent: '{intent_name}' | Confidence: {nlu_conf}")

        # 3️⃣ RAG
        contexts = self.rag.retrieve(text, k=4)
        context = "\n".join(contexts) if contexts else ""
        print(f"[DEBUG] RAG retrieved contexts: {contexts}")

        # 4️⃣ LLM
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

        # 5️⃣ Orchestrator (optional, WS layer is source of truth)
        orchestration_result = None
        if call_session:
            orchestration_result = self.orchestrator.process_turn(
                call_session=call_session,
                intent=detected_intent,
                asr_conf=asr_conf,
                nlu_conf=nlu_conf,
                ambiguous=False,
            )
            print(f"[DEBUG] Orchestrator turn result: {orchestration_result}")

        # 6️⃣ Return TEXT ONLY (WS decides if TTS happens)
        return {
            "text": text,
            "intent": intent_name,
            "asr_confidence": asr_conf,
            "nlu_confidence": nlu_conf,
            "response_text": response_text,
            "language": language,
            "orchestration_result": orchestration_result,
        }
