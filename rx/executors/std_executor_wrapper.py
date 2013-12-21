from rx.futures import Future
from concurrent.futures import ThreadPoolExecutor as TPX
from concurrent.futures import ProcessPoolExecutor as PPX


class ThreadPoolExecutor(TPX):
    def submit(self, fn, *args, **kwargs):
        cf = TPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    # assist type inference
    def __enter__(self):
        TPX.__enter__(self)
        return self


class ProcessPoolExecutor(PPX):
    def submit(self, fn, *args, **kwargs):
        cf = PPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    # assist type inference
    def __enter__(self):
        PPX.__enter__(self)
        return self
