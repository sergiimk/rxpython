from rx.futures import *
from rx.executors import ThreadPoolExecutor
import time
import functools
import unittest


class FutureTest(unittest.TestCase):
    def setUp(self):
        self.executor = ThreadPoolExecutor(max_workers=2)

    def tearDown(self):
        self.executor.shutdown()

    def testSuccessCallback(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        def on_success(res):
            self.clb_called = res

        f.on_success(on_success)
        f.on_failure(lambda _: self.fail('failure callback called on success'))

        self.assertFalse(self.clb_called)
        p.success(123)
        self.assertEqual(123, self.clb_called)

    def testFailureCallback(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        def on_failure(ex):
            self.assertIsInstance(ex, TypeError)
            self.clb_called = True

        f.on_failure(on_failure)
        f.on_success(lambda _: self.fail('success callback called on failure'))

        self.assertFalse(self.clb_called)
        p.failure(TypeError())
        self.assertTrue(self.clb_called)

    def testCallbackCalledAfterCompletion(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        p.success(123)

        def on_success(res):
            self.clb_called = res

        f.on_success(on_success)

        self.assertEqual(123, self.clb_called)

    def testCancellation(self):
        p = Promise()
        f = p.future

        self.assertFalse(p.is_cancelled)
        self.assertFalse(f.is_cancelled)

        f.cancel()

        self.assertTrue(p.is_cancelled)
        self.assertTrue(f.is_cancelled)

        p.failure(CancelledError())
        self.assertRaises(CancelledError, f.result)

    def testRecover(self):
        p = Promise()
        f = p.future
        fr = f.recover(lambda _: None)

        p.failure(TypeError())
        self.assertIsNone(fr.result())

    def testMapComposition(self):
        p = Promise()
        f1 = p.future
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        p.success(5)
        self.assertEqual(50, f3.result())

    def testMapExceptionPropagation(self):
        p = Promise()
        f1 = p.future
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        p.failure(TypeError())
        self.assertRaises(TypeError, f3.result)

    def testThenSuccess(self):
        def auth(): return self._success_after(0.01, True)

        def request(x): return self._success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        self.assertEqual(25, frequest.result(timeout=10))

    def testThenFailureFirst(self):
        def auth(): return Future.failed(IOError())

        def request(x): return self._success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        self.assertRaises(IOError, functools.partial(frequest.result, 10))

    def testThenFailureSecond(self):
        def auth(): return self._success_after(0.01, True)

        def request(x): return Future.failed(IOError())

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        self.assertRaises(IOError, functools.partial(frequest.result, 10))

    def testThenFailureFun(self):
        def auth(): return self._success_after(0.01, True)

        def request(x): raise AttributeError()

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        self.assertRaises(AttributeError, functools.partial(frequest.result, 10))

    def testFallback(self):
        def connect_plain(): return Future.failed(IOError())

        def connect_ssl(): return self._success_after(0.01, True)

        fconnect = connect_plain().fallback(connect_ssl)
        self.assertTrue(fconnect.result(timeout=10))

    def testAllCombinatorSuccess(self):
        futures = [self._success_after(0.01, i) for i in range(5)]
        fall = Future.all(futures).map(sum)
        self.assertEqual(sum(range(5)), fall.result(timeout=10))

    def testAllCombinatorFailure(self):
        futures = []

        for i in range(5):
            if i != 3:
                futures.append(self._success_after(0.01, i))
            else:
                futures.append(self._after(0.02, functools.partial(self._raise, TypeError())))

        fall = Future.all(futures).map(sum)
        self.assertRaises(TypeError, functools.partial(fall.result, 10))

    def testFirstCombinator(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        self._after(0.01, promises[2].success, 123)

        fall = Future.first(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def testFirstSuccessfulCombinator(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        self._after(0.01, promises[2].failure, TypeError())
        self._after(0.02, promises[4].success, 123)

        fall = Future.first_successful(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def testFirstSuccessfulCombinatorError(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        for p in promises:
            self._after(0.001, p.failure, TypeError())

        fall = Future.first_successful(futures)
        self.assertRaises(TypeError, functools.partial(fall.result, 10))

    def testReduceCombinator(self):
        futures = [self._success_after(0.01, i) for i in range(5)]
        fsum = Future.reduce(lambda x, y: x + y, futures)
        self.assertEqual(sum(range(5)), fsum.result(timeout=10))

    def _success_after(self, timeout, value):
        def do():
            time.sleep(timeout)
            return value

        return self.executor.submit(do)

    def _after(self, timeout, f, *vargs, **kwargs):
        def do():
            time.sleep(timeout)
            return f(*vargs, **kwargs)

        return self.executor.submit(do)

    def _raise(self, t):
        raise t


if __name__ == '__main__':
    unittest.main()
