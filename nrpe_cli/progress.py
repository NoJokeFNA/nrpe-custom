"""Optional presentation events; the controller remains the workflow owner."""

from contextlib import contextmanager
from contextvars import ContextVar

_listener = ContextVar('nrpe_progress_listener', default=None)


def notify(kind, **fields):
    listener = _listener.get()
    if listener is None:
        return False
    try:
        listener(kind, fields)
    except Exception:
        # Presentation failure must never change package verification or logs.
        _listener.set(None)
        return False
    return True


@contextmanager
def listen(callback):
    token = _listener.set(callback)
    try:
        yield
    finally:
        _listener.reset(token)
