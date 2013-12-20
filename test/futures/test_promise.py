from rx.futures import *
from concurrent.futures import ThreadPoolExecutor
import functools
import time
import unittest


class PromiseTest(unittest.TestCase):
    def setUp(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

    def testSucceeded(self):
        p = Promise()
        self.assertFalse(p.is_completed)

        p.success(10)
        self.assertTrue(p.is_completed)
        self.assertFalse(p.try_success(15))

        f = p.future
        self.assertTrue(f.is_completed)

        self.assertEqual(10, f.result())

    def testFailed(self):
        p = Promise()

        p.failure(TypeError())
        self.assertTrue(p.is_completed)

        f = p.future
        self.assertTrue(f.is_completed)
        self.assertFalse(p.try_failure(TimeoutError()))

        self.assertRaises(TypeError, f.result)

    def testResultAlreadyAssigned(self):
        p = Promise()
        p.success(123)
        self.assertRaises(IllegalStateError, lambda: p.success(321))
        self.assertRaises(IllegalStateError, lambda: p.failure(TypeError()))

    def testCompleteSuccess(self):
        p = Promise()
        p.complete(lambda: 123)
        self.assertEqual(123, p.future.result())

    def testCompleteFailure(self):
        def f():
            raise ArithmeticError()

        p = Promise()
        p.complete(f)
        self.assertRaises(ArithmeticError, p.future.result)

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
