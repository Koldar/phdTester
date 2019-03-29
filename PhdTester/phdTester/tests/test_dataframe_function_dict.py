import unittest

from phdTester.default_models import DataFrameFunctionsDict


class MyTestCase(unittest.TestCase):

    def test_01(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, 5)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [3, 4])

    def test_02(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f2", 3, 5)

        self.assertEqual(df.contains_function("f1"), True)
        self.assertEqual(df.contains_function("f2"), True)
        self.assertEqual(df.contains_function("f3"), False)

        self.assertEqual(df.contains_function_point("f1", 4), True)
        self.assertEqual(df.contains_function_point("f1", 3), False)
        self.assertEqual(df.contains_function_point("f2", 4), False)
        self.assertEqual(df.contains_function_point("f2", 3), True)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [4])
        self.assertEqual(list(df.get_ordered_x_axis("f2")), [3])

        self.assertEqual(list(df.get_ordered_xy("f1")), [(4, 2)])
        self.assertEqual(list(df.get_ordered_xy("f2")), [(3, 5)])

    def test_03(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, 5)
        df.update_function_point("f1", 2, 10)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [2, 3, 4])

        df.update_function_point("f2", 4, 2)
        df.update_function_point("f2", 5, 2)
        df.update_function_point("f2", 6, 2)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [2, 3, 4])
        self.assertEqual(list(df.get_ordered_x_axis("f2")), [4, 5, 6])

        df.remove_function_point("f2", 5)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [2, 3, 4])
        self.assertEqual(list(df.get_ordered_x_axis("f2")), [4, 6])

        df.remove_function_point("f1", 4)

        self.assertEqual(list(df.get_ordered_x_axis("f1")), [2, 3])
        self.assertEqual(list(df.get_ordered_x_axis("f2")), [4, 6])


if __name__ == '__main__':
    unittest.main()
