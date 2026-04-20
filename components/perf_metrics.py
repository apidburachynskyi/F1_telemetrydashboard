import time
import functools
from collections import deque
from prometheus_client import Histogram

TAB_DURATION = Histogram(
    "f1_tab_render_seconds",
    "Time to render each dashboard tab",
    ["tab"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30, 60],
)

RENDER_HISTORY = deque(maxlen=500)


def record(tab: str, duration: float):
    TAB_DURATION.labels(tab=tab).observe(duration)
    RENDER_HISTORY.append({"ts": time.time(), "tab": tab, "duration": duration})


def tab_timer(tab_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                record(tab_name, time.time() - t)

        return wrapper

    return decorator
