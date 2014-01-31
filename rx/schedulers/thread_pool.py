from .scheduler_base import SchedulerBase
from ..futures.multithreaded import Future
from ..config import Default
from concurrent.futures.thread import ThreadPoolExecutor


class ThreadPoolScheduler(SchedulerBase):
    def __init__(self, max_workers=None):
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def shutdown(self, wait=True):
        self.pool.shutdown(wait)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.pool.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, fn, *args, **kwargs):
        cff = self.pool.submit(fn, *args, **kwargs)
        cff.add_done_callback(self._execute_clb)

    def submit(self, fn, *args, **kwargs):
        future = self.pool.submit(fn, *args, **kwargs)
        return Future.convert(future)

    def _execute_clb(self, cff):
        exc = cff.exception()
        if exc is not None:
            Default.on_unhandled_error(exc)

