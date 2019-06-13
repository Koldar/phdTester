# TODO use these type instad of str!
import re

KS001Str = str
PathStr = str
DataTypeStr = str
RegexStr = str
"""
A string representing a python3.6 regular expression
"""

class SlottedClass(object):

    __slots__ = ()


class GetSuchInfo(object):
    """
    A class representing the return value of IDataSource.get_suchthat
    """
    __slots__ = ('path', 'name', 'type', 'ks001', 'tc')

    def __init__(self, path: PathStr, name: KS001Str, type: DataTypeStr, ks001: "KS001", tc: "ITestContext"):
        self.path = path
        self.name = name
        self.type = type
        self.ks001 = ks001
        self.tc = tc

    def __iter__(self):
        return (x for x in [self.path, self.name, self.type, self.ks001, self.tc])


class Interval(SlottedClass):
    """
    A class representing a mathematical interval between 2 real numbers.

    For example if can represents intervals like the following ones:
     - (5, 6)
     - (5, 6]
     - [5, 6)
     - [5, 6]
    """
    __slots__ = ('__lb', '__ub', '__lb_included', '__ub_included')

    def __init__(self, lb: float, ub: float, lb_included: bool, ub_included: bool):
        self.__lb = lb
        self.__lb_included = lb_included
        self.__ub = ub
        self.__ub_included = ub_included

    @property
    def lb(self) -> float:
        """
        :return: interval lowebound number
        """

        return self.__lb

    @property
    def ub(self) -> float:
        """

        :return: interval upperbound number
        """
        return self.__ub

    @property
    def lb_included(self) -> bool:
        """
        Checks if the lowerbound is included by "[" or by "("
        :return: true if the lowerbound is included in the interval.
        """
        return self.__lb_included

    @property
    def ub_included(self) -> bool:
        """
        Checks if the upperbound is included by "]" or by ")"
        :return: true if the upperbound is included in the interval.
        """
        return self.__ub_included

    def is_in(self, x: float) -> bool:
        """
        Checks if a number is included in a given interval
        :param x: the number involved
        :return: true if the number is inside an interval, false otherwise
        """
        if x == self.lb and self.lb_included:
            return True
        if x == self.ub and self.ub_included:
            return True
        return self.lb < x < self.ub

    def __str__(self):

        return "{lb_included}{lb}, {ub}{ub_included}".format(
            lb_included="[" if self.lb_included else "(",
            lb=self.lb,
            ub=self.ub,
            ub_included="]" if self.lb_included else ")",
        )

    @classmethod
    def parse(cls, string: str) -> "Interval":
        m = re.match(r"^\s*(?P<lb_included>[\(\[\)\]])\s*(?P<lb>[\+\-]?\d+\.?\d*)\s*,\s*(?P<ub>[\+\-]?\d+\.?\d*)\s*(?P<ub_included>[\(\[\)\]])\s*$", string)
        if m is None:
            raise ValueError(f"cannot parse \"{string}\" into {Interval.__class__.__name__}!")
        lb_included = m.group("lb_included") in ["[", ")"]
        ub_included = m.group("ub_included") in ["]", "("]
        lb = float(m.group("lb"))
        ub = float(m.group("ub"))

        return Interval(lb=lb, ub=ub, lb_included=lb_included, ub_included=ub_included)

