import whisper
import math


class ASRService:
    def __init__(self, model_name="base"):
        self.model = whisper.load_model(model_name)
        self._last_confidence = 0.0

    def transcribe_voice(self, audio_path: str) -> dict:
        """
        Transcribe audio file to text + language + confidence
        """
        result = self.model.transcribe(
            audio_path,
            fp16=False  # safer on Windows / CPU
        )

        text = result.get("text", "").strip()
        language = result.get("language", "unknown")

        segments = result.get("segments", [])
        if segments:
            avg_logprob = sum(
                s.get("avg_logprob", -1.0) for s in segments
            ) / len(segments)

            confidence = self.calibrate_confidence(avg_logprob)
        else:
            confidence = 0.0

        self._last_confidence = confidence

        return {
            "text": text,
            "language": language,
            "confidence": round(confidence, 2)
        }

    def get_confidence(self) -> float:
        return round(self._last_confidence, 2)

    @staticmethod
    def calibrate_confidence(avg_logprob: float) -> float:
        """
        Maps Whisper avg_logprob to human-friendly confidence [0,1]
        """
        return 1 / (1 + math.exp(-6 * (avg_logprob + 0.5)))
