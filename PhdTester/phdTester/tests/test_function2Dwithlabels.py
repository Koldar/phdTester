import unittest

from phdTester.default_models import PandasFunction2DWithLabel


class MyTestCase(unittest.TestCase):

    def test_01(self):
        f = PandasFunction2DWithLabel()

        self.assertEqual(f.number_of_points(), 0)

    def test_02(self):
        f = PandasFunction2DWithLabel()
        f.update_triple(3, 4, 5.6)

        self.assertEqual(f.number_of_points(), 1)
        self.assertEqual(f.has_x_value(5), False)
        self.assertEqual(f.has_x_value(3), True)
        self.assertEqual(f.has_x_value(4), False)
        self.assertAlmostEqual(f.get_y(3), 4, delta=0.1)
        self.assertAlmostEqual(f.get_label(3), 5.6, delta=0.1)

        f.remove_point(3)

        self.assertEqual(f.number_of_points(), 0)
        self.assertEqual(f.has_x_value(5), False)
        self.assertEqual(f.has_x_value(3), False)
        self.assertEqual(f.has_x_value(4), False)

    def test_03(self):
        f = PandasFunction2DWithLabel()
        f.update_triple(3, 4, 5.6)
        f.update_triple(4, 5, 5.6)

        f.remove_point(3)

        self.assertEqual(f.has_x_value(3), False)
        self.assertEqual(f.has_x_value(4), True)

    def test_04(self):
        f = PandasFunction2DWithLabel()
        f.update_triple(3, 4, 5.6)
        f.update_triple(3, 5, 5.7)

        self.assertEqual(f.has_x_value(3), True)
        self.assertEqual(f.get_y(3), 5)
        self.assertEqual(f.get_label(3), 5.7)

    def test_05(self):
        f = PandasFunction2DWithLabel()
        f.update_triple(1, 4, 10)
        f.update_triple(3, 5, 11)
        f.update_triple(2, 6, 12)

        self.assertEqual(list(f.x_ordered_values()), [1, 2, 3])
        self.assertEqual(list(f.y_ordered_value()), [4, 5, 6])
        labels = list(f.labels_unordered_values())
        self.assertIn(10, labels)
        self.assertIn(11, labels)
        self.assertIn(12, labels)
        val = list(f.xy_unordered_values())
        self.assertIn((1, 4), val)
        self.assertIn((2, 6), val)
        self.assertIn((3, 5), val)


if __name__ == '__main__':
    unittest.main()
