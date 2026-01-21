from backend.services.asr_service import ASRService
from backend.services.tts_service import TTSService

class VoicePipeline:
    def __init__(self):
        self.asr = ASRService()
        self.tts = TTSService()

    def process_audio(self, audio_path: str) -> dict:
        """
        Full voice loop:
        Audio → ASR → Text → TTS → Audio
        """

        asr_result = self.asr.transcribe_voice(audio_path)

        text = asr_result["text"]
        language = asr_result["language"]

        # Echo loop for now
        tts_audio_path = self.tts.synthesize(text=text, lang=language)

        return {
            "text": text,
            "language": language,
            "confidence": asr_result["confidence"],
            "audio_response": tts_audio_path
        }
