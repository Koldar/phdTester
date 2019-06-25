import unittest
import numpy as np

from phdTester import UpperBoundSlotValueFetcher
from phdTester.curve_changers.curves_changers import CheckNoInvalidNumbers, OverwriteFunctions, QuantizeXAxis, \
    CheckFunctions
from phdTester.image_computer.aggregators import MaxAggregator, MeanAggregator


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

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_03(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, float('+inf'), 10], "C": [9, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_04(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [float('-inf'), 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_05(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [9, 10, 11, 12, float('-inf')]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_06(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, np.nan, 9, 10], "C": [9, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_07(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [9, 10, 11, 12, np.nan]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_CheckNoInvalidNumbers_08(self):
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5],
            functions={"A": [3, 4, 5, 6, 7], "B": [6, 7, 8, 9, 10], "C": [np.nan, 10, 11, 12, 13]}
        ).alter_curves(None)

        with self.assertRaises(ValueError) as context:
            CheckNoInvalidNumbers().alter_curves(fd)

        self.assertTrue('a cell in curves is either NaN, +infinite or -infinite!' in context.exception.args)

    def test_QuantizeXAxis_01(self):
        """
        functions defined everywhere
        :return:
        """
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5, 6],
            functions={
                "A": [10, 15, 15, 10, 15, 15], "B": [20, 30, 30, 20, 30, 30], "C": [40, 50, 50, 40, 50, 50]}
        ).alter_curves(None)

        _, fd = QuantizeXAxis(
            quantization_levels=[0, 2, 4, 6],
            slot_value=UpperBoundSlotValueFetcher(),
            merge_method=MaxAggregator(),
        ).alter_curves(fd)

        CheckFunctions.from_dict(
            xaxis=[2, 4, 6],
            functions={
                "A": [15, 15, 15],
                "B": [30, 30, 30],
                "C": [50, 50, 50]
            }
        )

    def test_QuantizeXAxis_02(self):
        """
        functions not defined everywhere
        :return:
        """
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5, 6],
            functions={
                "A": [10, np.nan, 15, 10, 15, 15], "B": [20, 30, np.nan, np.nan, 30, 30], "C": [40, 50, 50, 40, np.nan, 50]}
        ).alter_curves(None)

        _, fd = QuantizeXAxis(
            quantization_levels=[0, 2, 4, 6],
            slot_value=UpperBoundSlotValueFetcher(),
            merge_method=MaxAggregator(),
        ).alter_curves(fd)

        CheckFunctions.from_dict(
            xaxis=[2, 4, 6],
            functions={
                "A": [10, 15, 15],
                "B": [30, np.nan, 30],
                "C": [50, 50, 50]
            }
        )

    def test_QuantizeXAxis_03(self):
        """
        functions not defined everywhere
        :return:
        """
        _, fd = OverwriteFunctions.from_dict(
            xaxis=[1, 2, 3, 4, 5, 6],
            functions={
                "A": [10, np.nan, 15, 10, 15, 15], "B": [20, 30, np.nan, np.nan, 30, 30], "C": [40, 50, 50, 40, np.nan, 50]}
        ).alter_curves(None)

        _, fd = QuantizeXAxis(
            quantization_levels=[0, 2, 4, 6],
            slot_value=UpperBoundSlotValueFetcher(),
            merge_method=MeanAggregator(),
        ).alter_curves(fd)

        CheckFunctions.from_dict(
            xaxis=[2, 4, 6],
            functions={
                "A": [10, 12.5, 15],
                "B": [25, np.nan, 30],
                "C": [45, 45, 50]
            }
        )



if __name__ == '__main__':
    unittest.main()
