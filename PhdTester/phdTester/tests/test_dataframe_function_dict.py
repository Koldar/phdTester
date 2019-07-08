import unittest
import numpy as np

from phdTester.functions import DataFrameFunctionsDict


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

    def test_04(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, 5)
        df.update_function_point("f1", 2, 10)

        df.update_function_point("f2", 4, 0)
        df.update_function_point("f2", 5, 5)
        df.update_function_point("f2", 7, 15)

        data = df.get_statistics("f1")
        self.assertEqual(data.count, 3)
        self.assertEqual(data.min, 2)
        self.assertEqual(data.max, 10)
        self.assertEqual(data.mean, (2+5+10)/3)
        self.assertEqual(data.median, 5)
        self.assertEqual(data.lower_percentile, 3.5)
        self.assertEqual(data.upper_percentile, 7.5)

        data = df.get_statistics("f2")
        self.assertEqual(data.count, 3)
        self.assertEqual(data.min, 0)
        self.assertEqual(data.max, 15)
        self.assertEqual(data.mean, (0 + 5 + 15) / 3)
        self.assertEqual(data.median, 5)
        self.assertEqual(data.lower_percentile, 2.5)
        self.assertEqual(data.upper_percentile, 10)

    def test_05(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, 5)
        df.update_function_point("f1", 2, 10)

        df.update_function_point("f2", 4, 0)
        df.update_function_point("f2", 5, 5)
        df.update_function_point("f2", 7, 15)

        statistic_dict = df.get_all_statistics()

        self.assertEqual(statistic_dict['f1'].count, 3)
        self.assertEqual(statistic_dict['f1'].min, 2)
        self.assertEqual(statistic_dict['f1'].max, 10)
        self.assertEqual(statistic_dict['f1'].mean, (2 + 5 + 10) / 3)
        self.assertEqual(statistic_dict['f1'].median, 5)
        self.assertEqual(statistic_dict['f1'].lower_percentile, 3.5)
        self.assertEqual(statistic_dict['f1'].upper_percentile, 7.5)

        self.assertEqual(statistic_dict['f2'].count, 3)
        self.assertEqual(statistic_dict['f2'].min, 0)
        self.assertEqual(statistic_dict['f2'].max, 15)
        self.assertEqual(statistic_dict['f2'].mean, (0 + 5 + 15) / 3)
        self.assertEqual(statistic_dict['f2'].median, 5)
        self.assertEqual(statistic_dict['f2'].lower_percentile, 2.5)
        self.assertEqual(statistic_dict['f2'].upper_percentile, 10)

    def test_06_replace_infinites_with_inplace(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, np.inf)
        df.update_function_point("f1", 2, 10)

        df.update_function_point("f2", 4, 0)
        df.update_function_point("f2", 5, 5)
        df.update_function_point("f2", 7, 15)

        expected_df = DataFrameFunctionsDict()

        expected_df.update_function_point("f1", 4, 2)
        expected_df.update_function_point("f1", 3, 10)
        expected_df.update_function_point("f1", 2, 10)

        expected_df.update_function_point("f2", 4, 0)
        expected_df.update_function_point("f2", 5, 5)
        expected_df.update_function_point("f2", 7, 15)

        df2 = df.replace_infinites_with(to_value=10, inplace=True)

        self.assertEqual(df2, expected_df)
        self.assertEqual(df.get_function_y("f1", 3), 10)

    def test_07_replace_infinites_without_inplace(self):
        df = DataFrameFunctionsDict()

        df.update_function_point("f1", 4, 2)
        df.update_function_point("f1", 3, np.inf)
        df.update_function_point("f1", 2, 10)

        df.update_function_point("f2", 4, 0)
        df.update_function_point("f2", 5, 5)
        df.update_function_point("f2", 7, 15)

        expected_df = DataFrameFunctionsDict()

        expected_df.update_function_point("f1", 4, 2)
        expected_df.update_function_point("f1", 3, 10)
        expected_df.update_function_point("f1", 2, 10)

        expected_df.update_function_point("f2", 4, 0)
        expected_df.update_function_point("f2", 5, 5)
        expected_df.update_function_point("f2", 7, 15)

        df2 = df.replace_infinites_with(to_value=10, inplace=False)

        self.assertEqual(df2, expected_df)
        self.assertEqual(df.get_function_y("f1", 3), np.inf)
        self.assertEqual(df2.get_function_y("f1", 3), 10)


if __name__ == '__main__':
    unittest.main()
