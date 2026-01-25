from typing import Union, List
import os
import subprocess
import uuid

from backend.services.asr_service import ASRService
from backend.services.tts_service import TTSService


class VoicePipeline:
    def __init__(self):
        self.asr = ASRService()
        self.tts = TTSService()

    def process_audio(self, audio_input: Union[str, List[str]]) -> dict:
        """
        Audio → ASR → (optional) TTS
        audio_input can be:
        - single audio path (classic mode)
        - list of chunk paths (streaming mode)
        """

        # ---- 1. Combine chunks if needed ----
        if isinstance(audio_input, list):
            audio_path = self._concat_chunks(audio_input)
            streaming = True
        else:
            audio_path = audio_input
            streaming = False

        # ---- 2. ASR ----
        asr_result = self.asr.transcribe_voice(audio_path)

        text = asr_result["text"]
        language = asr_result["language"]

        # ---- 3. TTS ONLY for non-streaming ----
        if not streaming:
            tts_audio_path = self.tts.synthesize(text=text, lang=language)
        else:
            tts_audio_path = None  # 🔑 important

        return {
            "text": text,
            "language": language,
            "confidence": asr_result["confidence"],
            "audio_response": tts_audio_path,
            "is_partial": streaming,
        }

    def _concat_chunks(self, chunk_paths: List[str]) -> str:
        """
        Concatenate WAV chunks without re-encoding.
        Safe for ASR context accumulation.
        """

        output_path = os.path.join("temp", f"concat_{uuid.uuid4().hex}.wav")

        # create ffmpeg concat file
        list_path = output_path.replace(".wav", ".txt")
        with open(list_path, "w") as f:
            for path in chunk_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                output_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        return output_path
