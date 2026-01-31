from backend.services.asr_service import ASRService
from backend.services.nlu_service import NLUService
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.services.tts_service import TTSService
from backend.controllers.orchestrator import Orchestrator
from concurrent.futures import ThreadPoolExecutor
import time


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

        self.executor = ThreadPoolExecutor(max_workers=3)

    def process_audio(self, audio_path: str, call_session=None) -> dict:
        """Process audio → text → intent → response (optimized with parallelization)."""
        start_time = time.time()

        asr_result = self.asr.transcribe_voice(audio_path)
        text = asr_result.get("text", "").strip()
        language = asr_result.get("language", "unknown")
        asr_conf = asr_result.get("confidence", 0.0)

        if not text or asr_conf < self.MIN_CONFIDENCE:
            return {
                "error": "asr_failed",
                "language": language,
                "confidence": asr_conf,
            }

        nlu_future = self.executor.submit(self.nlu.detect_intent, text)
        rag_future = self.executor.submit(self.rag.retrieve, text, 4)

        detected_intent = nlu_future.result()
        contexts = rag_future.result()

        nlu_conf = detected_intent.confidence if detected_intent else 0.0
        intent_name = detected_intent.name if detected_intent else "UNKNOWN"
        context = "\n".join(contexts) if contexts else ""

        try:
            response_text = self.llm.generate_response(
                user_text=text,
                context=context,
                language=language,
                intent=intent_name,
            )
        except Exception as e:
            response_text = "Je suis désolé, je n'ai pas pu générer de réponse."
            print(f"[LLM ERROR] {e}")

        orchestration_result = None
        if call_session:
            orchestration_result = self.orchestrator.process_turn(
                call_session=call_session,
                intent=detected_intent,
                asr_conf=asr_conf,
                nlu_conf=nlu_conf,
                ambiguous=False,
            )

        elapsed = time.time() - start_time
        print(f"[PERF] Total processing time: {elapsed:.2f}s")

        return {
            "text": text,
            "intent": intent_name,
            "asr_confidence": asr_conf,
            "nlu_confidence": nlu_conf,
            "response_text": response_text,
            "language": language,
            "orchestration_result": orchestration_result,
            "processing_time": round(elapsed, 2),
        }

    def __del__(self):
        """Cleanup thread pool."""
        self.executor.shutdown(wait=False)
