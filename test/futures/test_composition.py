from .test_base import FutureTestBase
from concurrent.futures.multithreaded import *


class FutureCompositionTest(FutureTestBase):
    def test_conversions_same(self):
        import concurrent.futures.cooperative as COOP
        import concurrent.futures.multithreaded as MT

        coop = COOP.Future()
        mt = MT.Future()

        self.assertIs(mt, MT.Future.convert(mt))
        self.assertIs(coop, COOP.Future.convert(coop))

    def test_conversions_mt_compatible_with_coop(self):
        import concurrent.futures.cooperative as COOP
        import concurrent.futures.multithreaded as MT

        coop = COOP.Future()
        self.assertIs(coop, MT.Future.convert(coop))

    def test_conversions_coop_incompatible_with_mt(self):
        import concurrent.futures.cooperative as COOP
        import concurrent.futures.multithreaded as MT

        mt = MT.Future()
        self.assertRaises(TypeError, COOP.Future.convert, mt)

    def test_asyncio_wrapping_mt(self):
        import concurrent.futures.multithreaded as MT
        import asyncio

        mt = MT.Future()
        self.assertIsNot(mt, asyncio.Future.convert(mt))

    def test_asyncio_composition_checks_for_same_loop(self):
        import asyncio

        f1 = asyncio.Future(loop=asyncio.new_event_loop())
        f2 = asyncio.Future(loop=asyncio.new_event_loop())

        self.assertRaises(ValueError, asyncio.Future.gather, [f1, f2])
        self.assertRaises(ValueError, asyncio.Future.first, [f1, f2])
        self.assertRaises(ValueError, asyncio.Future.first_successful, [f1, f2])

        f1 = asyncio.Future.failed(TypeError())
        f3 = f1.fallback(f2)
        self.assertRaises(ValueError, asyncio.get_event_loop().run_until_complete, f3)

    def test_recover_clb(self):
        f = Future()
        fr = f.recover(lambda _: None)

        f.set_exception(TypeError())
        self.assertIsNone(fr.result())

    def test_recover_value(self):
        f = Future()
        fr = f.recover(None)

        f.set_exception(TypeError())
        self.assertIsNone(fr.result())

    def test_recover_cancellation_back(self):
        f = Future()
        fr = f.recover(lambda _: None)

        fr.cancel()
        self.assertTrue(f.cancelled())

    def test_recover_cancellation_forth(self):
        f = Future()
        fr = f.recover(lambda _: None)

        f.cancel()
        self.assertTrue(fr.cancelled())

    def test_map(self):
        f1 = Future()
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        f1.set_result(5)
        self.assertEqual(50, f3.result())

    def test_map_cancellation_back(self):
        f1 = Future()
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        f3.cancel()
        self.assertTrue(f1.cancelled())

    def test_map_cancellation_forth(self):
        f1 = Future()
        f2 = f1.map(lambda x: x * x)
        f3 = f2.map(lambda x: x * 2)

        f1.cancel()
        self.assertTrue(f3.cancelled())

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

    def test_then_cancellation_back(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            return self.success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        frequest.cancel()
        self.assertTrue(fauth.cancelled())

    def test_then_cancellation_forth(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            return self.success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))

        fauth.cancel()
        self.assertTrue(frequest.cancelled())

    def test_then_first_failure(self):
        def auth():
            return Future.failed(IOError())

        def request(x):
            return self.success_after(0.01, x * x)

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(IOError, frequest.result, timeout=10)

    def test_then_second_failure(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            return Future.failed(IOError())

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(IOError, frequest.result, timeout=10)

    def test_then_fun_failure(self):
        def auth():
            return self.success_after(0.01, True)

        def request(x):
            raise AttributeError()

        fauth = auth()
        frequest = fauth.then(lambda: request(5))
        self.assertRaises(AttributeError, frequest.result, timeout=10)

    def test_fallback(self):
        def connect_plain():
            return Future.failed(IOError())

        def connect_ssl():
            return self.success_after(0.01, True)

        fconnect = connect_plain().fallback(connect_ssl)
        self.assertTrue(fconnect.result(timeout=10))

    def test_fallback_cancellation_back_1(self):
        def connect_plain():
            return self.raise_after(0.01, IOError())

        def connect_ssl():
            return self.success_after(0.01, True)

        f1 = connect_plain()
        f2 = f1.fallback(connect_ssl)

        f2.cancel()
        self.assertTrue(f1.cancelled())

    def test_fallback_cancellation_back_2(self):
        def connect_plain():
            return Future.failed(IOError())

        fmid = None

        def connect_ssl():
            nonlocal fmid
            fmid = self.success_after(0.01, True)
            return fmid

        f1 = connect_plain()
        f2 = f1.fallback(connect_ssl)

        f2.cancel()
        self.assertFalse(f1.cancelled())
        self.assertTrue(fmid.cancelled())

    def test_fallback_cancellation_forth(self):
        def connect_plain():
            return self.raise_after(0.01, IOError())

        def connect_ssl():
            return self.success_after(0.01, True)

        f1 = connect_plain()
        f2 = f1.fallback(connect_ssl)

        f1.cancel()
        self.assertTrue(f2.cancelled())

    def test_gather(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fall = Future.gather(futures).map(sum)
        self.assertEqual(sum(range(5)), fall.result(timeout=10))

    def test_gather_failure(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        futures[3] = self.raise_after(0.02, TypeError())

        fall = Future.gather(futures).map(sum)
        self.assertRaises(TypeError, fall.result, timeout=10)

    def test_gather_failure_as_result(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        futures[3] = self.raise_after(0.02, TypeError())

        fall = Future.gather(futures, return_exceptions=True)
        res = fall.result(timeout=10)
        self.assertIsInstance(res[3], TypeError)

        del res[3]
        self.assertListEqual([0, 1, 2, 4], res)

    def test_gather_cancellation_back(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fall = Future.gather(futures).map(sum)
        fall.cancel()
        self.assertTrue(all(map(Future.cancelled, futures)))

    def test_gather_cancellation_forth(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fall = Future.gather(futures).map(sum)
        futures[3].cancel()
        self.assertRaises(CancelledError, fall.result, timeout=10)
        self.assertFalse(all(map(Future.cancelled, futures)))

    def test_first(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.success_after(0.01, 123)

        fall = Future.first(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def test_first_cancellation_back(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.success_after(0.01, 123)

        fall = Future.first(futures)
        fall.cancel()
        self.assertTrue(all(map(Future.cancelled, futures)))

    def test_first_cancellation_forth(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.success_after(0.01, 123)

        fall = Future.first(futures)
        for f in futures:
            f.cancel()

        self.assertTrue(fall.cancelled())

    def test_first_successful(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.raise_after(0.01, TypeError())
        futures[4] = self.success_after(0.01, 123)

        fall = Future.first_successful(futures)
        self.assertEqual(123, fall.result(timeout=10))

    def test_first_successful_cancellation_back(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.raise_after(0.01, TypeError())
        futures[4] = self.success_after(0.01, 123)

        fall = Future.first_successful(futures)
        fall.cancel()
        self.assertTrue(all(map(Future.cancelled, futures)))

    def test_first_successful_cancellation_forth(self):
        futures = [Future() for _ in range(5)]
        futures[2] = self.raise_after(0.01, TypeError())
        futures[4] = self.success_after(0.01, 123)

        fall = Future.first_successful(futures)
        for f in futures:
            f.cancel()

        self.assertTrue(fall.cancelled())

    def test_first_successful_failure(self):
        futures = [self.raise_after(0.001, TypeError()) for _ in range(5)]
        fall = Future.first_successful(futures)
        self.assertRaises(TypeError, fall.result, timeout=10)

    def test_reduce(self):
        futures = [self.success_after(0.01, i) for i in range(5)]
        fsum = Future.reduce(futures, lambda x, y: x + y, 0)
        self.assertEqual(sum(range(5)), fsum.result(timeout=10))


if __name__ == '__main__':
    import unittest

    unittest.main()
