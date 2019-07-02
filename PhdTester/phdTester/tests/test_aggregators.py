import unittest

from phdTester.curve_changers.curves_changers import OverwriteFunctions, CheckFunctions
from phdTester.image_computer import aggregators


class MyTestCase(unittest.TestCase):

    def test_singleAggregators(self):
        _, fd1 = OverwriteFunctions.from_xaxis_dict({"A": [(1, 1), (2,2), (3,3)], "B": [(3,3), (4,4), (5,5)], "C": [(7,7), (8,8)], "D": [(14,14)]}).alter_curves(None)
        _, fd2 = OverwriteFunctions.from_xaxis_dict({"A": [(10, 10), (20, 20), (30, 30)], "B": [(6, 6), (7, 7), (8, 8)], "C": [(10, 10), (11, 11)]}).alter_curves(None)

        aggregator = aggregators.SingleAggregator()
        fdtotal = aggregator.with_pandas([fd1, fd2])

        CheckFunctions.from_xaxis_dict({
            "A": [(1,1), (2,2), (3, 3), (10, 10), (20, 20), (30, 30)],
            "B": [(3,3), (4,4,), (5,5), (6,6), (7,7), (8,8)],
            "C": [(7,7), (8,8), (10,10), (11,11)],
            "D": [(14,14)],
        }).alter_curves(fdtotal)

    def singleAggregatorsDuplicated(self):
        _, fd1 = OverwriteFunctions.from_xaxis_dict({
            "A": [(1, 1), (2, 2), (3, 3)],
            "B": [(3, 3), (4, 4), (5, 5)],
            "C": [(7, 7), (8, 8)],
            "D": [(14, 14)]
        }).alter_curves(None)
        _, fd2 = OverwriteFunctions.from_xaxis_dict({
            "A": [(10, 10), (20, 20), (30, 30)],
            "B": [(6, 6), (7, 7), (8, 8)],
            "C": [(10, 10), (7, 7)] # dupliacted entry
        }).alter_curves(None)

        aggregator = aggregators.SingleAggregator()

        with self.assertRaises(ValueError) as context:
            fdtotal = aggregator.with_pandas([fd1, fd2])


if __name__ == '__main__':
    unittest.main()
