from ..futures import Future
from concurrent.futures import ThreadPoolExecutor as TPX
from concurrent.futures import ProcessPoolExecutor as PPX
import logging
logger = logging.getLogger(__name__)


class ThreadPoolExecutor(TPX):
    def submit(self, fn, *args, **kwargs):
        cf = TPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    def execute(self, fn, *args, **kwargs):
        def safe():
            try:
                fn(*args, **kwargs)
            except:
                logger.exception("Unhandled error in executor")
        TPX.submit(self, safe)


class ProcessPoolExecutor(PPX):
    def submit(self, fn, *args, **kwargs):
        cf = PPX.submit(self, fn, *args, **kwargs)
        return Future.from_concurrent_future(cf)

    def execute(self, fn, *args, **kwargs):
        def safe():
            try:
                fn(*args, **kwargs)
            except:
                logger.exception("Unhandled error in executor")
        PPX.submit(self, safe)
