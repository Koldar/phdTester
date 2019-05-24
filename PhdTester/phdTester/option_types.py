# TODO maybe create a seaprate module
from typing import Any

from phdTester import commons
from phdTester.model_interfaces import IOptionType


class Int(IOptionType):
    """
    An option represents an integer
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return int

    def convert(self, value: Any) -> Any:
        return int(value)


class Str(IOptionType):
    """
    An option represents a string
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return str

    def convert(self, value: Any) -> Any:
        return str(value)


class Float(IOptionType):
    """
    An option represents a decimal value
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return float

    def convert(self, value: Any) -> Any:
        return float(value)


class Bool(IOptionType):
    """
    An option contain either true of false
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return bool

    def convert(self, value: Any) -> Any:
        return bool(value)


class IntList(IOptionType, list):
    """
    A list of integers
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return str

    def convert(self, value: Any) -> Any:
        return commons.safe_eval(value)


class BoolList(list):
    """
    A list of booleans
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return str

    def convert(self, value: Any) -> Any:
        return commons.safe_eval(value)


class FloatList(IOptionType, list):
    """
    A list of floats
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return str

    def convert(self, value: Any) -> Any:
        return commons.safe_eval(value)


class StrList(IOptionType, list):
    """
    A list of strings
    """

    def __init__(self):
        IOptionType.__init__(self)

    def to_argparse(self) -> type:
        return str

    def convert(self, value: Any) -> Any:
        return commons.safe_eval(value)
