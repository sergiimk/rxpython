from rx.futures import *
import unittest
import functools
from concurrent.futures import ThreadPoolExecutor
import time


class PromiseTest(unittest.TestCase):
    def setUp(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

    def testAlreadySucceeded(self):
        p = Promise()
        self.assertFalse(p.is_completed)

        p.success(10)
        self.assertTrue(p.is_completed)
        self.assertFalse(p.try_success(15))

        f = p.future
        self.assertTrue(f.is_completed)

        self.assertEqual(10, f.result())

    def testAlreadyFailed(self):
        p = Promise()

        p.failure(TypeError())
        self.assertTrue(p.is_completed)

        f = p.future
        self.assertTrue(f.is_completed)
        self.assertFalse(p.try_failure(TimeoutError()))

        self.assertRaises(TypeError, f.result)

    def testResultWaitTimeout(self):
        p = Promise()
        wait = functools.partial(p.future.result, 0)
        self.assertRaises(TimeoutError, wait)

    def testResultWaitCompletes(self):
        p = Promise()
        complete = functools.partial(p.success, 12345)
        self._run_async(complete, 0.01)

        f = p.future
        self.assertFalse(f.is_completed)
        self.assertTrue(f.wait(10))
        self.assertEqual(12345, f.result())

    def _run_async(self, f, timeout=0):
        def run_after():
            time.sleep(timeout)
            f()

        self.executor.submit(run_after)


if __name__ == '__main__':
    unittest.main()
