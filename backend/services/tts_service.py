import os
import uuid
import hashlib
import requests
from pathlib import Path
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "demo/tts_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class TTSService:
    """Text-to-Speech service using ElevenLabs with gTTS fallback and caching."""

    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.cache_dir = Path(OUTPUT_DIR) / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = "hpp4J3VqNfWAUOO0d1Us"
        self.elevenlabs_url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        )

        self.use_elevenlabs = bool(self.api_key)

        if not self.use_elevenlabs:
            print("[TTS] ElevenLabs API key not found, using gTTS fallback")
        else:
            print(f"[TTS] ElevenLabs initialized with voice: {self.voice_id}")

    def _get_cache_key(self, text: str, lang: str) -> str:
        """Generate cache key from text and language."""
        content = f"{text}_{lang}_{self.voice_id}".encode("utf-8")
        return hashlib.md5(content).hexdigest()

    def _synthesize_elevenlabs(self, text: str, output_path: str) -> bool:
        """
        Synthesize speech using ElevenLabs API.
        Returns True on success, False on failure.
        """
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.35,
                "similarity_boost": 0.45,
                "style": 0.0,
                "use_speaker_boost": False,
            },
        }

        try:
            response = requests.post(
                self.elevenlabs_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            print(f"[TTS] ElevenLabs success: {output_path}")
            return True

        except requests.exceptions.Timeout:
            print("[TTS] ElevenLabs timeout")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[TTS] ElevenLabs error: {e}")
            return False
        except Exception as e:
            print(f"[TTS] Unexpected error: {e}")
            return False

    def _synthesize_gtts(self, text: str, lang: str, output_path: str) -> bool:
        """
        Fallback synthesis using gTTS.
        Returns True on success, False on failure.
        """
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            print(f"[TTS] gTTS fallback success: {output_path}")
            return True
        except Exception as e:
            print(f"[TTS] gTTS error: {e}")
            return False

    def synthesize(self, text: str, lang: str = None) -> str:
        """
        Convert text to speech using ElevenLabs with caching.
        Falls back to gTTS if ElevenLabs fails.
        Returns path to the generated MP3 file, or None on failure.
        """
        if lang is None:
            lang = self.lang

        text = text.strip()
        if not text:
            return None

        cache_key = self._get_cache_key(text, lang)
        cached_file = self.cache_dir / f"tts_{cache_key}.mp3"

        if cached_file.exists():
            print(f"[TTS] Cache hit: {cached_file}")
            return str(cached_file)

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        if self.use_elevenlabs:
            if self._synthesize_elevenlabs(text, output_path):
                try:
                    import shutil

                    shutil.copy(output_path, cached_file)
                except Exception as e:
                    print(f"[TTS] Cache save failed: {e}")

                return output_path

        if self._synthesize_gtts(text, lang, output_path):
            try:
                import shutil

                shutil.copy(output_path, cached_file)
            except Exception as e:
                print(f"[TTS] Cache save failed: {e}")

            return output_path

        print("[TTS] All synthesis methods failed")
        return None
