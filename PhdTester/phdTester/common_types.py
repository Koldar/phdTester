# TODO use these type instad of str!
import abc

KS001Str = str
PathStr = str
DataTypeStr = str
RegexStr = str
"""
A string representing a python3.6 regular expression
"""


class SlottedClass(object):

    __slots__ = ()


class BoxData(SlottedClass):
    """
    Dumb object containing box plot data
    """

    __slots__ = ('count', 'min', 'max', 'lower_percentile', 'upper_percentile', 'median', 'mean', 'std')

    def __init__(self, count: int, min: float, lower_percentile: float, median: float, mean: float, upper_percentile: float, max: float, std: float):
        self.count = count
        self.min = min
        self.max = max
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
        self.median = median
        self.mean = mean
        self.std = std


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

        return self.__lb

    @property
    def ub(self) -> float:
        return self.__ub

    @property
    def lb_included(self) -> bool:
        return self.__lb_included

    @property
    def ub_included(self) -> bool:
        return self.__ub_included

    def is_in(self, x: float) -> bool:
        if x == self.lb and self.lb_included:
            return True
        if x == self.ub and self.ub_included:
            return True
        return self.lb < x < self.ub
