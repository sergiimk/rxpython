from rx.futures import *
import unittest


class PromiseTest(unittest.TestCase):
    def testAlreadySucceeded(self):
        p = Promise()
        self.assertFalse(p.is_completed)

        p.success(10)
        self.assertTrue(p.is_completed)
        self.assertFalse(p.try_success(15))

        f = p.future
        self.assertTrue(f.is_completed)

        self.assertEqual(10, f.result())

    def testAlreadyFailed(self):
        p = Promise()

        p.failure(TypeError())
        self.assertTrue(p.is_completed)

        f = p.future
        self.assertTrue(f.is_completed)
        self.assertFalse(p.try_failure(TimeoutError()))

        self.assertRaises(TypeError, f.result)


if __name__ == '__main__':
    unittest.main()
