from multiprocessing.util import info
from faster_whisper import WhisperModel
import math


class ASRService:
    def __init__(self, model_name="small"):
        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
        self._last_confidence = 0.0

    def transcribe_voice(self, audio_path: str) -> dict:

        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            best_of=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=3000),
        )

        text_parts = []
        logprobs = []

        for segment in segments:
            text_parts.append(segment.text)
            if segment.avg_logprob is not None:
                logprobs.append(segment.avg_logprob)

        text = " ".join(text_parts).strip()
        print("ASR output:", text)
        language = info.language if info and info.language else "fr"

        if logprobs:
            avg_logprob = sum(logprobs) / len(logprobs)
            confidence = self.calibrate_confidence(avg_logprob)
        else:
            confidence = 0.0

        self._last_confidence = confidence

        return {
            "text": text,
            "language": language,
            "confidence": round(confidence, 2),
        }

    def get_confidence(self) -> float:
        return round(self._last_confidence, 2)

    @staticmethod
    def calibrate_confidence(avg_logprob: float) -> float:
        return 1 / (1 + math.exp(-6 * (avg_logprob + 0.5)))
