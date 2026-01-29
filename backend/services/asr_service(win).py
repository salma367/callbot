from faster_whisper import WhisperModel
import math
import torch


class ASRService:
    def __init__(self, model_name="small"):
        # Check if CUDA is available for GPU acceleration
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        print(f"[ASR] Initializing Whisper on {device} with {compute_type}")

        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            num_workers=2,  # Parallel processing
            cpu_threads=4,  # CPU optimization
        )
        self._last_confidence = 0.0

    def transcribe_voice(self, audio_path: str) -> dict:
        """Optimized transcription with faster settings."""
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=3,  # Reduced from 5 (faster, minimal accuracy loss)
            best_of=3,  # Reduced from 5
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=1500,  # Reduced from 3000 (faster detection)
                threshold=0.5,  # VAD sensitivity
            ),
            word_timestamps=False,  # Disable if not needed
            condition_on_previous_text=False,  # Faster processing
        )

        text_parts = []
        logprobs = []

        for segment in segments:
            text_parts.append(segment.text)
            if segment.avg_logprob is not None:
                logprobs.append(segment.avg_logprob)

        text = " ".join(text_parts).strip()

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
