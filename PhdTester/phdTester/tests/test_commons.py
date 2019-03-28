import unittest

from phdTester import commons


class MyTestCase(unittest.TestCase):
    def test_expand_string(self):
        path = commons.expand_string("csvs/arena.map", [('/', '-')])
        self.assertEqual(path, "csvs-arena.map")


if __name__ == '__main__':
    unittest.main()
