from rx.futures import *
from rx.futures.config import Default
import unittest


class FutureCallbacksTest(unittest.TestCase):
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

    def testCallbackCalledPostCompletion(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        p.success(123)

        def on_success(res):
            self.clb_called = res

        f.on_success(on_success)

        self.assertEqual(123, self.clb_called)

    def testCancellationFiresFailureCallback(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        def on_failure(ex):
            self.assertIsInstance(ex, CancelledError)
            self.clb_called = True

        f.on_failure(on_failure)
        f.on_success(lambda _: self.fail('success callback called on failure'))

        self.assertFalse(self.clb_called)
        f.cancel()
        self.assertTrue(self.clb_called)

    def testUnhandledErrorHandler(self):
        self.clb_called = False

        def on_unhandled(ex):
            self.clb_called = ex

        Default.UNHANDLED_FAILURE_CALLBACK = on_unhandled

        f = Future.successful(123)
        f.on_success(lambda _: self._raise(TypeError()))

        self.assertIsInstance(self.clb_called, TypeError)

    def _raise(self, t):
        raise t


if __name__ == '__main__':
    unittest.main()
