from rx.futures import *
from .test_base import FutureTestBase
import functools


class FutureCoreTest(FutureTestBase):
    def test_get_result_when_succeeded(self):
        p = Promise()
        self.assertFalse(p.is_completed)
        self.assertFalse(p.is_cancelled)

        p.success(10)
        self.assertTrue(p.is_completed)
        self.assertFalse(p.is_cancelled)
        self.assertFalse(p.try_success(15))

        f = p.future
        self.assertTrue(f.is_completed)
        self.assertFalse(f.is_cancelled)

        self.assertEqual(10, f.result())

    def test_get_result_when_failed(self):
        p = Promise()

        p.failure(TypeError())
        self.assertFalse(p.is_cancelled)
        self.assertTrue(p.is_completed)

        f = p.future
        self.assertTrue(f.is_completed)
        self.assertFalse(f.is_cancelled)
        self.assertFalse(p.try_failure(TimeoutError()))

        self.assertRaises(TypeError, f.result)

    def test_get_result_when_cancelled(self):
        p = Promise()

        f = p.future
        self.assertTrue(f.cancel())

        self.assertTrue(p.is_cancelled)
        self.assertTrue(p.is_completed)

        self.assertTrue(f.is_cancelled)
        self.assertTrue(f.is_completed)

        self.assertTrue(p.try_success(123))
        self.assertTrue(p.try_failure(TimeoutError()))
        self.assertFalse(f.cancel())

        self.assertRaises(CancelledError, f.result)

    def test_get_exception_when_succeeded(self):
        p = Promise()
        p.success(10)
        f = p.future
        self.assertIsNone(f.exception())

    def test_get_exception_when_failed(self):
        p = Promise()
        p.failure(TypeError())
        f = p.future
        self.assertIsInstance(f.exception(), TypeError)

    def test_get_exception_when_cancelled(self):
        p = Promise()
        f = p.future
        f.cancel()
        self.assertIsInstance(f.exception(), CancelledError)

    def test_set_result_when_already_set(self):
        p = Promise()
        p.success(123)
        self.assertRaises(IllegalStateError, lambda: p.success(321))
        self.assertRaises(IllegalStateError, lambda: p.failure(TypeError()))

    def test_complete_successfully(self):
        p = Promise()
        p.complete(lambda: 123)
        self.assertEqual(123, p.future.result())

    def test_complete_with_exception(self):
        def f():
            raise ArithmeticError()

        p = Promise()
        p.complete(f)
        self.assertRaises(ArithmeticError, p.future.result)

    def test_wait_raises_timeout(self):
        p = Promise()
        wait = functools.partial(p.future.result, 0)
        self.assertRaises(TimeoutError, wait)

    def test_wait_succeeds(self):
        f = self.success_after(0.01, 12345)
        self.assertFalse(f.is_completed)
        self.assertTrue(f.wait(10))
        self.assertEqual(12345, f.result())


if __name__ == '__main__':
    import unittest

    unittest.main()
