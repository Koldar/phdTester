import abc
import logging
from typing import Iterable, List, Any, Tuple

import pandas as pd

from phdTester import commons
from phdTester.model_interfaces import ITestContextRepo, ITestContext, ITestContextMask, ITestContextRepoView, \
    IOptionDict, IUnderTesting, ITestingEnvironment, IStuffUnderTestMask, ITestEnvironmentMask, \
    ITestingGlobalSettings, ICsvRow, IFunction2D, IFunction2DWithLabel, IDataWriter


class GnuplotDataWriter(IDataWriter):
    """
    Gnuplot sucks!
    """

    def __init__(self, filename: str, separator: str = " ", alias: str = "", carriage_return: str = "\n"):
        self.filename = filename
        self.alias = alias
        self.separator = separator
        self.carriage_return = carriage_return
        self._file = None

    def __enter__(self):
        self._file = open(self.filename, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def writeline(self, data: Iterable[Any]):
        if any(map(lambda x: isinstance(x, str), data)):
            return
        self._file.write(self.separator.join(map(lambda x: x.replace(self.separator, self.alias), map(lambda x: str(x), data))) + self.carriage_return)


class CsvDataWriter(IDataWriter):

    def __init__(self, filename: str, separator: str = ","):
        self.filename = filename
        self.separator = separator
        self._file = None

    def __enter__(self):
        self._file = open(self.filename, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def writeline(self, data: Iterable[Any]):
        self._file.write(self.separator.join(map(lambda x: x.replace(self.separator, ""), map(lambda x: str(x), data))) + "\n")


class Function2D(commons.SlottedClass, IFunction2D):
    """
    Represents a function y=f(x). The function is merely a set of 2D points, so it's more like a mapping.
    Functions have no names
    """

    __slots__ = ('_function', '_sortedx', '_sortedx_valid')

    def __init__(self):
        super().__init__()
        self._function = {}
        self._sortedx = []
        """
        A list of sorted x values. Introduced to cache the order to the x values
        """
        self._sortedx_valid: bool = False
        """
        true if the field _sortedx is actually representing the sorted set of _function, false otherwise
        """

    @classmethod
    def from_xy(cls, x: Iterable[float], y: Iterable[float]) -> "IFunction2D":
        """
        Create a new function from 2 lists of the same length
        :param x: the x values
        :param y: the y values
        :return: a new function
        """
        result = cls()
        for x, y in zip(x, y):
            result.update_point(x, y)
        return result

    def update_point(self, x: float, y: float):
        """
        adds a point in the function.
        If the value was already present the old value is overwritten

        :param x: the x vlaue to add
        :param y: the y value to add
        """
        self._function[x] = y
        self._sortedx_valid = False

    def remove_point(self, x: float):
        self._sortedx_valid = False
        del self._function[x]

    def get_y(self, x: float) -> float:
        """

        :param x: the x value whose y value we need to fetch
        :return: the y value associated to the x value
        """
        return self._function[x]

    def number_of_points(self) -> int:
        return len(self._function)

    def x_unordered_values(self) -> Iterable[float]:
        """

        :return: iterable of x values. Order is **not** garantueed
        """
        return self._function.keys()

    def change_ith_x(self, x_index: int, new_value: float):
        super(Function2D, self).change_ith_x(x_index, new_value)
        self._sortedx_valid = False

    def change_x(self, old_x: float, new_x: float, overwrite: bool = False):
        super(Function2D, self).change_x(old_x, new_x, overwrite)
        self._sortedx_valid = False

    def x_ordered_values(self) -> Iterable[float]:
        """

        :return: iterable of x values. Order goes from the lowest till the greatest
        """
        if not self._sortedx_valid:
            self._sortedx = list(sorted(self._function.keys()))
            self._sortedx_valid = True
        return self._sortedx

    def y_unordered_value(self) -> Iterable[float]:
        """

        :return: iterable of y values. Order is **not** garantueed
        """
        return self._function.values()

    def xy_unordered_values(self) -> Iterable[Tuple[float, float]]:
        """

        :return: iterable of pair os x,y. Order is **not** garantueed
        """
        return self._function.items()


class SeriesFunction(commons.SlottedClass, IFunction2D):

    __slots__ = ('_series', '_max_x')

    def __init__(self):
        super(SeriesFunction, self).__init__()
        self._series = pd.Series([])
        self._max_x = float('-inf')

    def update_point(self, x: float, y: float):
        self._series[x] = y
        if x > self._max_x:
            self._max_x = x
        else:
            # the index may not be sorted anymore. We need to sort it back
            self._series.sort_index(inplace=True)

    def remove_point(self, x: float):
        del self._series[x]
        if len(self._series) > 0:
            if x == self._max_x:
                self._max_x = self._series.index[self._series.idxmax()]
        else:
            self._max_x = float('-inf')

    def get_y(self, x: float) -> float:
        return self._series[x]

    def number_of_points(self) -> int:
        return len(self._series)

    def x_unordered_values(self) -> Iterable[float]:
        return self._series.index

    def x_ordered_values(self):
        return self._series.index

    def y_unordered_value(self) -> Iterable[float]:
        return self._series.values


class PandasFunction(commons.SlottedClass, IFunction2D):

    __slots__ = ('df', )

    def __init__(self):
        super().__init__()
        self.df = pd.DataFrame(columns=['x', 'y'])
        self.df.set_index('x', inplace=True)

    def update_point(self, x: float, y: float):
        # FIXME this is called lots of time and it slow down application
        self.df.loc[x] = [y]

    def has_x_value(self, x: float) -> bool:
        return x in self.df.index

    def remove_point(self, x: float):
        self.df.drop(x, axis=0, inplace=True)

    def get_y(self, x: float) -> float:
        return float(self.df.loc[x]['y'])

    def number_of_points(self) -> int:
        return self.df.shape[0]

    def x_unordered_values(self) -> Iterable[float]:
        return iter(self.df.index)

    def y_unordered_value(self) -> Iterable[float]:
        return self.df.loc[:, 'y']


class StandardOptionDict(IOptionDict):
    """
    Implementation of IOptionDict which directly queries all the public attributes of the object attached to it.

    Use only when:
     - the subtype has __dict__ attribute (if it's a class this is ensured by default)
     - the attributes you care about are public and are not properties (tagged with @proiperty)
     - it's not implemented as a tuple (so no __slots__ schenanigans)
    """

    def __init__(self):
        IOptionDict.__init__(self)

    def options(self) -> Iterable[str]:
        return (name for name in vars(self) if not name.startswith('_'))

    def get_option(self, name: str) -> Any:
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options")
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options")
        self.__dict__[name] = value


class AbstractTestingGlobalSettings(ITestingGlobalSettings, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingGlobalSettings.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractStuffUnderTest(IUnderTesting, StandardOptionDict, abc.ABC):

    def __init__(self):
        IUnderTesting.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestingEnvironment(ITestingEnvironment, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingEnvironment.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestContext(ITestContext, abc.ABC):

    def __init__(self, ut: "IUnderTesting", te: "ITestingEnvironment"):
        ITestContext.__init__(self, ut=ut, te=te)


class AbstractStuffUnderTestMask(IStuffUnderTestMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        IStuffUnderTestMask.__init__(self)


class AbstractTestEnvironmentMask(ITestEnvironmentMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingEnvironment.__init__(self)


class AbstractTestContextMask(ITestContextMask, abc.ABC):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        ITestContextMask.__init__(self, ut=ut, te=te)


def _query_by_mask(m: "ITestContextMask", iterable: Iterable["ITestContext"]) -> Iterable["ITestContext"]:
    for tc in iterable:
        if m.is_complaint_with_test_context(tc, list(iterable)):
            yield tc


class AbstractCSVRow(ICsvRow, StandardOptionDict, abc.ABC):
    """
    A csv row which natively implements all the IOptionDict methods by looking at  __dict__ public fields
    of the subtype
    """

    def __init__(self):
        ICsvRow.__init__(self)
        StandardOptionDict.__init__(self)


class SimpleTestContextRepoView(ITestContextRepoView):

    def __init__(self, values: Iterable[ITestContext], repo: "ITestContextRepo"):
        self.values = list(values)
        self._repo = repo

    def __iter__(self) -> Iterable[ITestContext]:
        return iter(self.values)

    def __getitem__(self, item: int) -> "ITestContext":
        return self.values[item]

    @property
    def repository(self) -> "ITestContextRepo":
        return self._repo

    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        return SimpleTestContextRepoView(list(_query_by_mask(m, self.values)), self._repo)

    def __len__(self) -> int:
        return len(self.values)


class SimpleTestContextRepo(ITestContextRepo):

    def __init__(self):
        ITestContextRepo.__init__(self)
        self.repo: List["ITestContext"] = []

    def append(self, v: "ITestContext"):
        self.repo.append(v)

    def __iter__(self) -> Iterable[ITestContext]:
        return iter(self.repo)

    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        return SimpleTestContextRepoView(list(_query_by_mask(m, self.repo)), self)

    def query_by_finding_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        """
        like query_by_mask but we autyomatically check if there is only one result and, if so, we return it
        :param m: the mask to apply
        :return:  the single element computed
        :raises ValueError: if the query returns 0 or more than 1 element
        """
        result = list(self.query_by_mask(m))
        if len(result) != 1:
            logging.critical("We obtained {} elements:\ntest context mask: {}\nelements:{}".format(len(result), str(m), "\n".join(map(str, result))))
            raise ValueError(f"we expected to have 1 element, not {len(result)}!")
        return result[0]

    def __len__(self) -> int:
        return len(self.repo)

    def clear(self):
        self.repo.clear()

