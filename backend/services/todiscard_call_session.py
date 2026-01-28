import uuid
from typing import List


class CallSession:
    def __init__(self):
        self.session_id = uuid.uuid4().hex
        self.audio_chunks: List[str] = []
        self.conversation_log: List[dict] = []
        self.is_ai_turn: bool = True  # AI speaks first

    def add_chunk(self, path: str):
        self.audio_chunks.append(path)

    def get_buffered_audio(self):
        # For now, concat all chunks or just take last chunk
        return self.audio_chunks[-1] if self.audio_chunks else None

    def log_turn(self, speaker: str, text: str, audio_response: str = None):
        self.conversation_log.append(
            {"speaker": speaker, "text": text, "audio_response": audio_response}
        )

    def clear(self):
        self.audio_chunks = []
        self.conversation_log = []
