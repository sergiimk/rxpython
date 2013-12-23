from .test_base import FutureTestBase
from concurrent.futures.async import *


class FutureCompositionTest(FutureTestBase):
    def test_recover(self):
        f = Future()
        fr = f.recover(lambda _: None)

        f.set_exception(TypeError())
        self.assertIsNone(fr.result())

    def test_map(self):
        f1 = Future()
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        f1.set_result(5)
        self.assertEqual(50, f3.result())

    def test_map_propagates_failure(self):
        f1 = Future()
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        f1.set_exception(TypeError())
        self.assertRaises(TypeError, f3.result)

    def test_then(self):
        def auth():
            return Future.successful(True)

        def request(x):
            return self.success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertEqual(25, frequest.result(timeout=10))

    def test_then_first_failure(self):
        def auth():
            return Future.failed(IOError())

        def request(x):
            return self.success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(IOError, frequest.result, 10)

    def test_then_second_failure(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            return Future.failed(IOError())

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(IOError, frequest.result, 10)

    def test_then_fun_failure(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            raise AttributeError()

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(AttributeError, frequest.result, 10)

    def test_fallback(self):
        def connect_plain():
            return Future.failed(IOError())

        def connect_ssl():
            return self.success_after(0.01, True)

        fconnect = connect_plain().fallback(connect_ssl)
        self.assertTrue(fconnect.result(timeout=10))

    def test_all(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fall = Future.all(futures).map(sum)
        self.assertEqual(sum(range(5)), fall.result(timeout=10))

    def test_all_failure(self):
        futures = []

        for i in range(5):
            if i != 3:
                futures.append(self.success_after(0.01, i))
            else:
                futures.append(self.raise_after(0.02, TypeError()))

        fall = Future.all(futures).map(sum)
        self.assertRaises(TypeError, fall.result, 10)

    def test_first(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.success_after(0.01, 123)

        fall = Future.first(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def test_first_successful(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.raise_after(0.01, TypeError())
        futures[4] = self.success_after(0.01, 123)

        fall = Future.first_successful(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def test_first_successful_failure(self):
        futures = [self.raise_after(0.001, TypeError()) for _ in range(5)]
        fall = Future.first_successful(futures)
        self.assertRaises(TypeError, fall.result, 10)

    def test_reduce(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fsum = Future.reduce(futures, lambda x, y: x + y, 0)
        self.assertEqual(sum(range(5)), fsum.result(timeout=10))


if __name__ == '__main__':
    import unittest

    unittest.main()
