from threading import Lock


class Cancellable(object):
    def __init__(self, initial=False):
        self._cancelled = initial
        self._mutex = Lock()

    @property
    def is_cancelled(self):
        with self._mutex:
            return self._cancelled

    def cancel(self):
        with self._mutex:
            self._cancelled = True
