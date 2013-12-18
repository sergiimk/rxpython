from rx.futures import *
from concurrent.futures import ThreadPoolExecutor
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
        def auth():
            p = Promise()
            self._success_after(p, True, 0.01)
            return p.future

        def request(x):
            p = Promise()
            self._success_after(p, x * x, 0.01)
            return p.future

        fauth = auth()
        frequest = fauth.then(request, 5)

        self.assertEqual(25, frequest.result(timeout=10))

    def testThenFailureFirst(self):
        def auth():
            return Future.failed(IOError())

        def request(x):
            p = Promise()
            self._success_after(p, x * x, 0.01)
            return p.future

        fauth = auth()
        frequest = fauth.then(request, 5)

        self.assertRaises(IOError, functools.partial(frequest.result, 10))

    def testAllCombinatorSuccess(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        for i, p in enumerate(promises):
            self._success_after(p, i, 0.01)

        fall = Future.all(futures).map(sum)
        self.assertEqual(sum(range(5)), fall.result(timeout=10))

    def testAllCombinatorFailure(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        for i, p in enumerate(promises):
            if i != 3:
                self._success_after(p, i, 0.01)
            else:
                self._after(functools.partial(p.failure, TypeError()), 0.02)

        fall = Future.all(futures).map(sum)
        self.assertRaises(TypeError, functools.partial(fall.result, 10))

    def testFirstCombinator(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        self._success_after(promises[4], 123, 0.01)

        fall = Future.first(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def testReduceCombinator(self):
        promises = [Promise() for _ in range(5)]
        futures = [p.future for p in promises]

        for i, p in enumerate(promises):
            self._success_after(p, i, 0.01)

        fsum = Future.reduce(lambda x, y: x + y, futures)
        self.assertEqual(sum(range(5)), fsum.result(timeout=10))

    def _success_after(self, p, res, timeout):
        def s():
            time.sleep(timeout)
            p.success(res)
        self.executor.submit(s)

    def _after(self, f, timeout):
        def ff():
            time.sleep(timeout)
            f()
        self.executor.submit(ff)

if __name__ == '__main__':
    unittest.main()
