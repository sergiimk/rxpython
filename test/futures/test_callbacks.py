from .test_base import FutureTestBase
from concurrent.futures.sync import *
from concurrent.futures.config import Default


class FutureCallbacksTest(FutureTestBase):
    def test_on_success_callback(self):
        f = Future()
        self.clb_called = False

        def on_done(fut):
            self.clb_called = fut.result()

        f.add_done_callback(on_done)

        self.assertFalse(self.clb_called)
        f.set_result(123)
        self.assertEqual(123, self.clb_called)

    def test_on_failure_callback(self):
        f = Future()
        self.clb_called = False

        def on_done(fut):
            self.clb_called = fut.exception()

        f.add_done_callback(on_done)

        self.assertFalse(self.clb_called)
        f.set_exception(TypeError())
        self.assertIsInstance(self.clb_called, TypeError)

    def test_callbacks_called_post_completion(self):
        f = Future()
        self.clb_called = False

        f.set_result(123)

        def on_done(fut):
            self.clb_called = fut.result()

        f.add_done_callback(on_done)
        self.assertEqual(123, self.clb_called)

    def test_cancelling_fires_callback(self):
        f = Future()
        self.clb_called = False

        def on_done(fut):
            self.assertRaises(CancelledError, fut.exception)
            self.clb_called = True

        f.add_done_callback(on_done)

        self.assertFalse(self.clb_called)
        f.cancel()
        self.assertTrue(self.clb_called)

    def test_unhandled_error_future(self):
        self.clb_called = False

        def on_unhandled(cls, tb):
            self.clb_called = cls

        Default.UNHANDLED_FAILURE_CALLBACK = staticmethod(on_unhandled)

        f = Future.completed(self._raise, TypeError())
        f._ex_handler.__del__()
        self.assertEqual(TypeError, self.clb_called)

    def test_unhandled_error_callback(self):
        self.clb_called = False

        def on_unhandled(cls, tb):
            self.clb_called = cls

        Default.UNHANDLED_FAILURE_CALLBACK = staticmethod(on_unhandled)

        f = Future.successful(123)
        f.add_done_callback(lambda _: self._raise(TypeError()))
        self.assertEqual(TypeError, self.clb_called)


if __name__ == '__main__':
    import unittest
    unittest.main()
