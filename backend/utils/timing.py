import time
from contextlib import contextmanager


@contextmanager
def timer(label: str, timings: dict):
    start = time.time()
    yield
    timings[label] = round(time.time() - start, 3)
