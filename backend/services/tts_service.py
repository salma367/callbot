import os
import uuid
import hashlib
from functools import lru_cache
from gtts import gTTS
from pathlib import Path

OUTPUT_DIR = "demo/tts_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class TTSService:
    """Text-to-Speech service using gTTS with caching."""

    def __init__(self, lang: str = "fr"):
        self.lang = lang
        self.cache_dir = Path(OUTPUT_DIR) / "cache"
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, text: str, lang: str) -> str:
        """Generate cache key from text and language."""
        content = f"{text}_{lang}".encode("utf-8")
        return hashlib.md5(content).hexdigest()

    def synthesize(self, text: str, lang: str = None) -> str:
        """
        Convert text to speech using gTTS with caching.
        Returns path to the generated MP3 file, or None on failure.
        """
        if lang is None:
            lang = self.lang

        text = text.strip()
        if not text:
            return None

        # Check cache first
        cache_key = self._get_cache_key(text, lang)
        cached_file = self.cache_dir / f"tts_{cache_key}.mp3"

        if cached_file.exists():
            return str(cached_file)

        # Generate new audio
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)

            # Save to cache as well
            tts.save(str(cached_file))

            return output_path
        except Exception as e:
            print(f"[TTS ERROR] gTTS failed: {e}")
            return None
