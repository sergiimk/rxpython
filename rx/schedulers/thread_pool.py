from .scheduler_base import SchedulerBase
from ..futures.multithreaded import Future
from concurrent.futures.thread import ThreadPoolExecutor


class ThreadPoolScheduler(SchedulerBase):
    def __init__(self, max_workers=None):
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def shutdown(self, wait=True):
        self.pool.shutdown(wait)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.pool.__exit__(exc_type, exc_val, exc_tb)

    def submit(self, func, *vargs, **kwargs):
        future = self.pool.submit(func, *vargs, **kwargs)
        return Future.convert(future)
