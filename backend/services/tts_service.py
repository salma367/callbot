import os
import uuid
from gtts import gTTS

OUTPUT_DIR = "demo/tts_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class TTSService:
    """
    Text-to-Speech service using gTTS (Google Text-to-Speech).
    """

    def __init__(self, lang: str = "fr"):
        self.lang = lang

    def synthesize(self, text: str, lang: str = None) -> str:
        """
        Convert text to speech using gTTS.
        Returns path to the generated MP3 file, or None on failure.
        """
        if lang is None:
            lang = self.lang

        text = text.strip()
        # Optional: add small pause by prepending punctuation
        text = f"{text}"

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            print(f"[TTS] Generated audio: {output_path}")
            return output_path
        except Exception as e:
            print(f"[TTS ERROR] gTTS failed: {e}")
            return None
