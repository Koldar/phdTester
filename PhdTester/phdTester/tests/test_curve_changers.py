import unittest
import numpy as np

from phdTester.curve_changers.curves_changers import CheckNoInvalidNumbers, OverwriteFunctions


class MyTestCase(unittest.TestCase):

    def test_CheckNoInvalidNumbers_01(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3],
            functions={"A": [3, 4, 5], "B": [6, 7, 8], "C": [9, 10, 11]}
        ).alter_curves(None)
        CheckNoInvalidNumbers().alter_curves(fd)

    def test_CheckNoInvalidNumbers_02(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, float('+inf'), 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [9, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_03(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, float('+inf'), 10], "C": [9, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_04(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [float('-inf'), 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_05(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [9, 10, 11, 12, float('-inf')]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_06(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, np.nan, 9, 10], "C": [9, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_07(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [9, 10, 11, 12, np.nan]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)

    def test_CheckNoInvalidNumbers_08(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [np.nan, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception)


if __name__ == '__main__':
    unittest.main()
