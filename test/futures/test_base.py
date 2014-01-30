from rx.schedulers import ThreadPoolScheduler
import unittest
import time


class FutureTestBase(unittest.TestCase):
    def setUp(self):
        self.scheduler = ThreadPoolScheduler(max_workers=2)

    def tearDown(self):
        self.scheduler.shutdown()

    def async(self, fun, timeout=0):
        def run_after():
            time.sleep(timeout)
            fun()

        f = self.scheduler.submit(run_after)
        f.add_done_callback(None)

    def success_after(self, timeout, value):
        def do():
            time.sleep(timeout)
            return value

        return self.scheduler.submit(do)

    def raise_after(self, timeout, exception):
        def do():
            time.sleep(timeout)
            raise exception

        return self.scheduler.submit(do)

    def _raise(self, t):
        raise t
