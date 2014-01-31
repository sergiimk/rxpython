from rx.schedulers import ThreadPoolScheduler
from rx.futures.multithreaded import *
import time
import math
import functools
import unittest


class ThreadPoolExecutorTest(unittest.TestCase):
    def test_submit_success(self):
        with ThreadPoolScheduler(1) as tpx:
            f = tpx.submit(lambda: math.factorial(10))
            self.assertEqual(3628800, f.result(timeout=10))

    def test_submit_failure(self):
        with ThreadPoolScheduler(1) as tpx:
            def error():
                raise TypeError()

            f = tpx.submit(error)
            self.assertRaises(TypeError, functools.partial(f.result, timeout=10))

    def test_cancellation(self):
        with ThreadPoolScheduler(1) as tpx:
            tpx.submit(time.sleep, 0.01)
            f = tpx.submit(math.factorial, 10)
            f.cancel()
            self.assertRaises(CancelledError, f.result)

    def test_raises_with_no_timeout(self):
        f = Future()
        self.assertRaises(InvalidStateError, f.result)
        self.assertRaises(InvalidStateError, f.exception)

    def test_timeouts(self):
        f = Future()
        self.assertRaises(TimeoutError, f.result, timeout=0)
        self.assertRaises(TimeoutError, f.exception, timeout=0)

    def test_callback_executor(self):
        import threading

        with ThreadPoolScheduler(1) as tpx1:
            with ThreadPoolScheduler(1) as tpx2:
                thread_main = threading.current_thread()
                thread_body = 1
                thread_clb = 2

                def run():
                    time.sleep(0.01)
                    nonlocal thread_body
                    thread_body = threading.current_thread()

                def clb(_):
                    time.sleep(0.01)
                    nonlocal thread_clb
                    thread_clb = threading.current_thread()

                f = tpx1.submit(run)
                f2 = f.map(clb, executor=tpx2)

                f2.result(timeout=10)
                self.assertNotEqual(thread_main, thread_body)
                self.assertNotEqual(thread_main, thread_clb)
                self.assertNotEqual(thread_body, thread_clb)


if __name__ == '__main__':
    unittest.main()
