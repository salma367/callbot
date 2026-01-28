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
        self.voice_id = "pqHfZKP75CvOlQylNhV4"

    def synthesize(self, text: str, lang: str = "fr") -> str:
        """
        Low-latency, slower-paced TTS using ElevenLabs.
        """

        text = text.strip()
        text = f"<break time='200ms'/> {text}"

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        url = f"{self.base_url}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,  # higher = faster + calmer
                "similarity_boost": 0.45,  # lower = faster
                "style": 0.3,  # slower speaking pace
                "use_speaker_boost": False,  # faster
            },
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            print(f" ElevenLabs TTS failed: {e}")
            return None

        return output_path
