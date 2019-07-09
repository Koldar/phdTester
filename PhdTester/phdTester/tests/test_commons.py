import abc
import unittest

from phdTester import commons


class IFoo(abc.ABC):

    @abc.abstractmethod
    def foo(self, name: str) -> str:
        pass


class FooImpl(IFoo):

    def foo(self, name: str) -> str:
        return f"{name} FooImpl"


def function_foo(name: str) -> str:
    return f"{name} function_foo"


class MyTestCase(unittest.TestCase):

    def test_expand_string(self):
        path = commons.expand_string("csvs/arena.map", [('/', '-')])
        self.assertEqual(path, "csvs-arena.map")

    def test_direct_call_or_method_call(self):

        foo = FooImpl()

        self.assertEqual(commons.direct_call_or_method_call(foo, "foo", "world"), f"world FooImpl")
        self.assertEqual(commons.direct_call_or_method_call(foo, IFoo.foo, "world"), f"world FooImpl")
        self.assertEqual(commons.direct_call_or_method_call(function_foo, "foo", "world"), f"world function_foo")
        self.assertEqual(commons.direct_call_or_method_call(lambda name: f"{name} lambda", "foo", "world"), f"world lambda")


if __name__ == '__main__':
    unittest.main()
