from rx.observables.cooperative import Observable, StreamEndError, CancelledError
from rx.config import Default
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

    def test_exception(self):
        obs = Observable()
        obs.set_exception(TimeoutError())

        self.assertTrue(obs.done())
        f = obs.next()

        self.assertIsInstance(f.exception(), TimeoutError)
        self.assertIsInstance(obs.exception(), TimeoutError)

    def test_unhandled_error(self):
        self.clb_called = False

        def on_unhandled(cls, tb):
            self.clb_called = cls

        Default.UNHANDLED_FAILURE_CALLBACK = staticmethod(on_unhandled)

        obs = Observable()
        obs.set_exception(TypeError())
        obs._ex_handler.__del__()
        self.assertEqual(TypeError, self.clb_called)



if __name__ == '__main__':
    unittest.main()
