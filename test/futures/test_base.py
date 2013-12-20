from rx.executors import ThreadPoolExecutor
import unittest
import time


class FutureTestBase(unittest.TestCase):
    def setUp(self):
        self.executor = ThreadPoolExecutor(max_workers=2)

    def tearDown(self):
        self.executor.shutdown()

    def async(self, fun, timeout=0):
        def run_after():
            time.sleep(timeout)
            fun()

        f = self.executor.submit(run_after)
        f.on_failure(None)

    def success_after(self, timeout, value):
        def do():
            time.sleep(timeout)
            return value

        return self.executor.submit(do)

    def raise_after(self, timeout, exception):
        def do():
            time.sleep(timeout)
            raise exception

        return self.executor.submit(do)

    def _raise(self, t):
        raise t
