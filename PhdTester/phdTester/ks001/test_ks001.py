import unittest

from phdTester.ks001.ks001 import KS001


class MyTestCase(unittest.TestCase):

    def test_01(self):
        expected = KS001()
        expected.add_key_value(0, "a", 5)
        string = "|a=5|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_02(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value(0, "a", 5)
        string = "hello|a=5|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_03(self):
        expected = KS001()
        expected.identifier = "hello|"
        expected.add_key_value(0, "a", 5)
        string = "hello|||a=5|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_04(self):
        expected = KS001()
        expected.identifier = "hel=lo"
        expected.add_key_value(0, "a", 5)
        string = "hel==lo|a=5|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_05(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value(0, "a|", 5)
        string = "hello|a||=5|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_06(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value(0, "a", 5)
        expected.add_key_value(0, "b", 8)
        string = "hello|a=5_b=8|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_07(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value(0, "a", 5)
        expected.add_key_value(0, "b_b", 8)
        string = "hello|a=5_b__b=8|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_08(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        string = "hello|d1:a=5_b=8|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_09(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value("d:1", "a", 5)
        expected.add_key_value("d:1", "b", 8)
        string = "hello|d::1:a=5_b=8|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_10(self):
        expected = KS001()
        expected.identifier = "hello"
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        expected.add_key_value("d2", "foo", "ciao")
        string = "hello|d1:a=5_b=8|d2:foo=ciao|"
        actual = KS001.parse_str(string)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_11(self):
        expected = KS001()
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        expected.add_key_value("d2", "foo", "ciao")
        string = "|d1:a=5_b=8|d2:foo=ciao|"
        actual = KS001.parse_str(string )
        self.assertEqual(actual, expected)

    def test_12(self):
        expected = KS001()
        expected.add_key_alias("foo", "f")
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        expected.add_key_value("d2", "foo", "ciao")

        string = "|d1:a=5_b=8|d2:f=ciao|"
        actual = KS001.parse_str(string, key_alias=expected.key_aliases)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_13(self):
        expected = KS001()
        expected.add_value_alias("ciao", "c")
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        expected.add_key_value("d2", "foo", "ciao")

        string = "|d1:a=5_b=8|d2:foo=c|"
        actual = KS001.parse_str(string, value_alias=expected.value_aliases)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_14(self):
        expected = KS001()
        expected.add_value_alias("ciao", "c")
        expected.add_key_value("d1", "a", 5)
        expected.add_key_value("d1", "b", 8)
        expected.add_empty_dictionary("d2")

        string = "|d1:a=5_b=8|d2:|"
        actual = KS001.parse_str(string, value_alias=expected.value_aliases)
        self.assertEqual(actual, expected)
        self.assertEqual(expected.dump_str(), string)

    def test_add_01(self):
        a = KS001()
        a.add_key_value(0, "a", 3)
        a.add_key_value(0, "b", 5)

        b = KS001()
        b.add_key_value(0, "c", 8)
        b.add_key_value(0, "d", 9)

        self.assertEqual(len(a+b), 2)
        self.assertEqual((a+b).dump_str(), "|a=3_b=5|c=8_d=9|")

    def test_add_02(self):
        a = KS001()
        a.add_key_value(0, "a", 3)
        a.add_key_value(0, "b", 5)

        b = KS001()
        b.add_key_value("other", "c", 8)
        b.add_key_value("other", "d", 9)

        self.assertEqual(len(a+b), 2)
        self.assertEqual((a+b).dump_str(), "|a=3_b=5|other:c=8_d=9|")


if __name__ == '__main__':
    unittest.main()
