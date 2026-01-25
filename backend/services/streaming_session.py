import time
from collections import deque


class StreamingSession:
    def __init__(self):
        self.audio_chunks = deque()
        self.last_activity = time.time()
        self.text_buffer = []

    def add_chunk(self, audio_path: str):
        self.audio_chunks.append(audio_path)
        self.last_activity = time.time()

    def get_buffered_audio(self):
        return list(self.audio_chunks)

    def clear(self):
        self.audio_chunks.clear()
        self.text_buffer.clear()
