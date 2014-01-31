import unittest


class StreamEndError(Exception):
    pass


class ObservableTest(unittest.TestCase):
    def test_foo(self):
        pass


if __name__ == '__main__':
    #unittest.main()
    import asyncio
    import logging
    logging.basicConfig(level=logging.DEBUG)

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
            return self



    @asyncio.coroutine
    def process():
        s = source()

        futures = [s.get_next() for _ in range(10)]
        res = yield from asyncio.gather(*futures, return_exceptions=True)
        print(res)


        #for f in s:
        #    val = yield from f
        #    print(val)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(process())
