from rx.observables import Observable, StreamEndError, CancelledError
import unittest


class ObservableTest(unittest.TestCase):
    def test_callbacks(self):
        obs = Observable()
        send = [1, 2, 3]
        self.recv = []

        def clb(obs, fut):
            self.recv.append(fut.result())

        obs.add_observe_callback(clb)
        for v in send:
            obs.set_next_value(v)

        self.assertListEqual(send, self.recv)

    def test_end_marker(self):
        obs = Observable()
        self.assertFalse(obs.done())

        self.recv = None

        def clb(obs, fut):
            self.recv = fut.exception()

        obs.add_observe_callback(clb)
        obs.set_end()
        self.assertTrue(obs.done())
        self.assertIsInstance(self.recv, StreamEndError)

    def test_end_callback_post_completion(self):
        obs = Observable()
        obs.set_end()
        self.recv = None

        def clb(obs, fut):
            self.recv = fut.exception()

        obs.add_observe_callback(clb)
        self.assertIsInstance(self.recv, StreamEndError)

    def test_cancelling_fires_callback(self):
        obs = Observable()
        self.assertFalse(obs.cancelled())
        self.recv = None

        def clb(obs, fut):
            self.recv = fut.exception()

        obs.add_observe_callback(clb)
        obs.cancel()
        self.assertTrue(obs.cancelled())
        self.assertIsInstance(self.recv, CancelledError)

    def test_cancel_callback_post_completion(self):
        obs = Observable()
        obs.cancel()
        self.recv = None

        def clb(obs, fut):
            self.recv = fut.exception()

        obs.add_observe_callback(clb)
        self.assertIsInstance(self.recv, CancelledError)



if __name__ == '__main__':
    unittest.main()

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