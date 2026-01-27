import os
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "demo/tts_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class TTSService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise EnvironmentError("Please set ELEVENLABS_API_KEY environment variable")
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

        self.voice_id = "hpp4J3VqNfWAUOO0d1Us"

    def synthesize(self, text: str, lang: str = "fr") -> str:
        """
        Convert text to speech using ElevenLabs.
        Returns path to mp3 file.
        """

        # Add filler sounds randomly for more human-like effect
        import random

        fillers = ["Hmm...", "Euh...", "Uhh..."]
        if random.random() < 0.3:
            text = random.choice(fillers) + " " + text

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        url = f"{self.base_url}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.7},
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            # Save audio content
            with open(output_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            print(f"❌ ElevenLabs TTS failed: {e}")
            return None

        return output_path
