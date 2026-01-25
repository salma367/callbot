import subprocess
from pathlib import Path


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
