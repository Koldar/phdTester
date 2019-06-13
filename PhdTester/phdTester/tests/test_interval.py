import unittest

from phdTester import common_types
from phdTester.common_types import Interval


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(Interval.parse("[5,6]"), Interval(5.0, 6.0, True, True))
        self.assertEqual(Interval.parse("[5,6)"), Interval(5, 6, True, False))
        self.assertEqual(Interval.parse("(5,6]"), Interval(5, 6, False, True))
        self.assertEqual(Interval.parse("(5,6)"), Interval(5, 6, False, False))
        self.assertEqual(Interval.parse("]5,6]"), Interval(5, 6, False, True))
        self.assertEqual(Interval.parse("[5,6["), Interval(5, 6, True, False))
        self.assertEqual(Interval.parse("]5,6["), Interval(5, 6, False, False))

    def test_contains_01(self):
        a = Interval(5, 10, True, True)
        self.assertEqual(a.contains(6), True)
        self.assertEqual(a.contains(5), True)
        self.assertEqual(a.contains(10), True)
        self.assertEqual(a.contains(1), False)
        self.assertEqual(a.contains(20), False)

    def test_contains_02(self):
        a = Interval(5, 10, False, True)
        self.assertEqual(a.contains(6), True)
        self.assertEqual(a.contains(5), False)
        self.assertEqual(a.contains(10), True)
        self.assertEqual(a.contains(1), False)
        self.assertEqual(a.contains(20), False)

    def test_contains_03(self):
        a = Interval(5, 10, True, False)
        self.assertEqual(a.contains(6), True)
        self.assertEqual(a.contains(5), True)
        self.assertEqual(a.contains(10), False)
        self.assertEqual(a.contains(1), False)
        self.assertEqual(a.contains(20), False)

    def test_contains_04(self):
        a = Interval(5, 10, False, False)
        self.assertEqual(a.contains(6), True)
        self.assertEqual(a.contains(5), False)
        self.assertEqual(a.contains(10), False)
        self.assertEqual(a.contains(1), False)
        self.assertEqual(a.contains(20), False)


if __name__ == '__main__':
    unittest.main()
