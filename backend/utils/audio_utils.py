import subprocess
from pathlib import Path
import wave
import audioop


def normalize_for_asr(input_path: str, output_path: str):

    input_path = Path(input_path)
    output_path = Path(output_path)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def is_silent_wav(path: str, rms_threshold: int = 300) -> bool:
    """
    Returns True if audio energy is below threshold (silence).
    Threshold ~200–500 is reasonable for 16-bit PCM.
    """
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            rms = audioop.rms(frames, wf.getsampwidth())
            print(f"[AUDIO] RMS energy = {rms}")
            return rms < rms_threshold
    except Exception as e:
        print(f"[AUDIO][ERROR] Silence check failed: {e}")
        return True  # fail-safe: treat as silence
