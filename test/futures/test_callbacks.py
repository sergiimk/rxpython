from .test_base import FutureTestBase
from rx.futures import *
from rx.futures.config import Default


class FutureCallbacksTest(FutureTestBase):
    def test_on_success_callback(self):
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

    def test_on_failure_callback(self):
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

    def test_callbacks_called_post_completion(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        p.success(123)

        def on_success(res):
            self.clb_called = res

        f.on_success(on_success)

        self.assertEqual(123, self.clb_called)

    def test_cancelling_fires_failure_callback(self):
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

    def test_unhandled_error_handler(self):
        self.clb_called = False

        def on_unhandled(ex):
            self.clb_called = ex

        Default.UNHANDLED_FAILURE_CALLBACK = staticmethod(on_unhandled)

        f = Future.successful(123)
        f.on_success(lambda _: self._raise(TypeError()))

        self.assertIsInstance(self.clb_called, TypeError)


if __name__ == '__main__':
    import unittest

    unittest.main()
