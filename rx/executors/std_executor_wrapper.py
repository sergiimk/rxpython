from rx.futures import Future
from concurrent.futures import ThreadPoolExecutor as TPX
from concurrent.futures import ProcessPoolExecutor as PPX


class ThreadPoolExecutor(TPX):
    def submit(self, fn, *args, **kwargs) -> Future:
        cf = TPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    def execute(self, fn, *args, **kwargs):
        return self.submit(fn, *args, **kwargs)


class ProcessPoolExecutor(PPX):
    def submit(self, fn, *args, **kwargs) -> Future:
        cf = PPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    def execute(self, fn, *args, **kwargs):
        return self.submit(fn, *args, **kwargs)
