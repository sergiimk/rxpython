from concurrent.futures.cooperative import *
from .test_base import FutureTestBase
import functools


class FutureCoreTest(FutureTestBase):
    def test_repr(self):
        f = Future()
        f.add_done_callback(functools.partial(self._raise, TypeError()))
        f.add_done_callback(functools.partial(self._raise, TypeError()))
        f.add_done_callback(functools.partial(self._raise, TypeError()))
        repr(f)

    def test_type_checks(self):
        import concurrent.futures.cooperative as coop
        import concurrent.futures.multithreaded as mt
        from concurrent.futures import FutureBase

        fcoop = coop.Future()
        fmt = mt.Future()

        self.assertIsInstance(fcoop, FutureBase)
        self.assertIsInstance(fmt, FutureBase)

    def test_get_result_when_succeeded(self):
        f = Future()
        self.assertFalse(f.done())
        self.assertFalse(f.cancelled())

        f.set_result(10)
        self.assertTrue(f.done())
        self.assertFalse(f.cancelled())
        self.assertFalse(f.try_set_result(15))
        self.assertEqual(10, f.result())

    def test_get_result_when_failed(self):
        f = Future()

        f.set_exception(TypeError())
        self.assertFalse(f.cancelled())
        self.assertTrue(f.done())

        self.assertFalse(f.try_set_exception(TimeoutError()))
        self.assertRaises(TypeError, f.result)

    def test_get_result_when_cancelled(self):
        f = Future()
        self.assertTrue(f.cancel())

        self.assertTrue(f.cancelled())
        self.assertTrue(f.done())

        self.assertTrue(f.try_set_result(123))
        self.assertTrue(f.try_set_exception(TimeoutError()))
        self.assertFalse(f.cancel())

        self.assertRaises(CancelledError, f.result)

    def test_get_exception_when_succeeded(self):
        f = Future()
        f.set_result(10)
        self.assertIsNone(f.exception())

    def test_get_exception_when_failed(self):
        f = Future()
        f.set_exception(TypeError())
        self.assertIsInstance(f.exception(), TypeError)

    def test_get_exception_when_cancelled(self):
        f = Future()
        f.cancel()
        self.assertRaises(CancelledError, f.exception)

    def test_set_result_when_already_set(self):
        f = Future()
        f.set_result(123)
        self.assertRaises(InvalidStateError, lambda: f.set_result(321))
        self.assertRaises(InvalidStateError, lambda: f.set_exception(TypeError()))


if __name__ == '__main__':
    import unittest

    unittest.main()
