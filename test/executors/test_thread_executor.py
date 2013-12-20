from rx.executors import *
from rx.futures import *
import time
import math
import functools
import unittest


class ThreadPoolExecutorTest(unittest.TestCase):
    def testSubmitSuccess(self):
        with ThreadPoolExecutor(1) as tpx:
            f = tpx.submit(lambda: math.factorial(10))
            self.assertEqual(3628800, f.result(timeout=10))

    def testSubmitFailure(self):
        with ThreadPoolExecutor(1) as tpx:
            def error():
                raise TypeError()

            f = tpx.submit(error)
            self.assertRaises(TypeError, functools.partial(f.result, 10))

    def testCancellation(self):
        with ThreadPoolExecutor(1) as tpx:
            tpx.submit(time.sleep, 0.01)
            f = tpx.submit(math.factorial, 10)
            f.cancel()
            self.assertRaises(CancelledError, f.result)


if __name__ == '__main__':
    unittest.main()
