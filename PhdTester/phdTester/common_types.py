from typing import Union


class Int:
    pass


class Str:
    pass


class Float:
    pass


class Bool:
    pass


class PercentageInt(str):
    """
    A string which ends with a percentage symbol.

    Allowed values are "5", "5%" or "5.3%".
    The regex is:

    \d+|\d+%|\d+.\d+%
    """
    pass


# class IntExpr(str):
#     """
#     An evaluatable string which, if evaluate, generates an integer.
#
#     For example the string "int(0.1*V)" represents an cevaluatable integer.
#     When V=40, the expression lead to the integer 4
#     """
#     pass
#
#
# class FloatExpr(str):
#     """
#     An evaluatable string which, if evaluate, generates a float
#     """
#     pass


class IntList(list):
    """
    A list of integers
    """
    pass


class BoolList(list):
    """
    A list of booleans
    """
    pass


class FloatList(list):
    """
    A list of floats
    """
    pass


class StrList(list):
    """
    A list of strings
    """
    pass


class PercentageIntList(list):
    """
    A list of evaluatable integers
    """
    pass

# class IntExprList(list):
#     """
#     A list of evaluatable integers
#     """
#     pass
#
#
# class FloatExprList(list):
#     """
#     A list of evaluatable floats
#     """
#     pass


AvailableOptionType = Union[
    Int, Float, Bool, Str,
    IntList, FloatList, BoolList, StrList,
    PercentageInt,
    PercentageIntList
]