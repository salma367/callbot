from gtts import gTTS
import uuid
import os

OUTPUT_DIR = "demo/tts_outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


class TTSService:
    def synthesize(self, text: str, lang: str = "fr") -> str:
        """
        Convert text to speech.
        Returns path to mp3 file.
        """

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        tts = gTTS(text=text, lang=lang)
        tts.save(output_path)

        return output_path
