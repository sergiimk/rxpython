from rx.observables.cooperative import Observable, Future, StreamEndError, CancelledError
import asyncio
import unittest


class ObservableTest(unittest.TestCase):
    def test_full_iteration(self):
        obs = Observable()
        self.recv = []
        loop = asyncio.get_event_loop()

        def produce(i):
            if i < 5:
                obs.set_next_value(i)
                loop.call_soon(produce, i + 1)
            else:
                obs.set_completed()

        @asyncio.coroutine
        def consume():
            loop.call_soon(produce, 0)

            for f in obs:
                yield from Future.to_asyncio_future(f)
                self.recv.append(f.result())

        loop.run_until_complete(consume())
        self.assertListEqual([0, 1, 2, 3, 4], self.recv)

    def test_cancel_iteration(self):
        obs = Observable()
        self.recv = []
        loop = asyncio.get_event_loop()

        def produce(i):
            if not obs.cancelled():
                obs.set_next_value(i)
                loop.call_soon(produce, i + 1)

        @asyncio.coroutine
        def consume():
            loop.call_soon(produce, 0)

            try:
                for f in obs:
                    yield from Future.to_asyncio_future(f)
                    self.recv.append(f.result())
                    if len(self.recv) == 5:
                        obs.cancel()
            except CancelledError:
                self.recv.append(None)

        loop.run_until_complete(consume())
        self.assertListEqual([0, 1, 2, 3, 4, None], self.recv)

if __name__ == '__main__':
    unittest.main()
