from rx.futures import *
import unittest


class FutureTest(unittest.TestCase):
    def testSuccessCallback(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        def on_success(res):
            self.clb_called = res
        f.on_success(on_success)
        f.on_failure(lambda _: self.fail('failure callback called on success'))

        self.assertFalse(self.clb_called)
        p.success(123)
        self.assertEqual(123, self.clb_called)

    def testFailureCallback(self):
        p = Promise()
        f = p.future
        self.clb_called = False

        def on_failure(ex):
            self.assertIsInstance(ex, TypeError)
            self.clb_called = True
        f.on_failure(on_failure)
        f.on_success(lambda _: self.fail('success callback called on failure'))

        self.assertFalse(self.clb_called)
        p.failure(TypeError())
        self.assertTrue(self.clb_called)


if __name__ == '__main__':
    unittest.main()
