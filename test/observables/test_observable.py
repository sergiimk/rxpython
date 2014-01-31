from rx.observables import Observable, StreamEndError
import unittest


class ObservableTest(unittest.TestCase):
    def test_foo(self):
        pass


if __name__ == '__main__':
    #unittest.main()
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)

    def tick(i, obs):
        obs.set_next_value(i)
        if i < 4:
            asyncio.get_event_loop().call_later(0.5, tick, i + 1, obs)
        else:
            obs.set_end()

    def process():
        obs = Observable()
        asyncio.get_event_loop().call_soon(tick, 0, obs)

        futures = [obs.next() for _ in range(10)]


        def clb(obs, fut):
            print(futures)
            #print(obs, fut)
            if isinstance(fut.exception(), StreamEndError):
                asyncio.get_event_loop().stop()

        obs.add_observe_callback(clb)

    process()
    loop = asyncio.get_event_loop()
    loop.run_forever()


'''
class source:
    def __init__(self):
        self.i = 0
        self.last = 5

    @asyncio.coroutine
    def recv(self):
        yield from asyncio.sleep(0.5)

        if self.i == self.last:
            raise StreamEndError()
        else:
            r = self.i
            self.i += 1
            return r

    def get_next(self):
        return self.recv()

    def __next__(self):
        if self.i == self.last:
            raise StopIteration()
        return self.recv()

    def __iter__(self):
        return self'''