import abc
import logging
from typing import Iterable, List, Any, Tuple, Dict

import numpy as np
import pandas as pd

from phdTester import commons
from phdTester.model_interfaces import ITestContextRepo, ITestContext, ITestContextMask, ITestContextRepoView, \
    IOptionDict, IStuffUnderTest, ITestEnvironment, IStuffUnderTestMask, ITestEnvironmentMask, \
    ITestingGlobalSettings, ICsvRow, IFunction2D, IDataWriter, IFunctionsDict


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

    def to_series(self) -> pd.Series:
        return pd.Series(self._function)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.to_series())


class SeriesFunction(commons.SlottedClass, IFunction2D):

    __slots__ = ('_series', '_max_x')

    def __init__(self):
        super(SeriesFunction, self).__init__()
        self._series = pd.Series([])
        self._max_x = float('-inf')


    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "SeriesFunction":
        result = cls()

        result._series = pd.Series(df)
        result._max_x = result._series.max()

        return result

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

    def to_series(self) -> pd.Series:
        return self._series

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self._series)


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

    def to_series(self) -> pd.Series:
        return self.df.loc[:, 'y']

    def to_dataframe(self) -> pd.DataFrame:
        return self.df


class StandardFunctionsDict(commons.SlottedClass, IFunctionsDict):
    """
    A class which saves the different functions inside a dict
    """

    __slots__ = ("_dictionary", )

    def __init__(self):
        super().__init__()
        self._dictionary: Dict[str, "IFunction2D"] = {}

    def function_names(self) -> Iterable[str]:
        yield from self._dictionary.keys()

    def functions(self) -> Iterable["IFunction2D"]:
        yield from self._dictionary.values()

    def size(self) -> int:
        return len(self._dictionary)

    def max_function_length(self) -> int:
        return max(map(lambda name: self.get_function(name).number_of_points(), self.function_names()))

    def get_function(self, name: str) -> "IFunction2D":
        return self._dictionary[name]

    def set_function(self, name, f: "IFunction2D"):
        self._dictionary[name] = f

    def remove_function(self, name: str):
        del self._dictionary[name]

    def contains_function_point(self, name: str, x: float) -> bool:
        return self._dictionary[name].has_x_value(x)

    def get_function_y(self, name: str, x: float) -> float:
        return self._dictionary[name].get_y(x)

    def update_function_point(self, name: str, x: float, y: float):
        self._dictionary[name].update_point(x, y)

    def remove_function_point(self, name: str, x: float):
        self._dictionary[name].remove_point(x)

    def contains_function(self, name: str) -> bool:
        return name in self._dictionary

    def get_ordered_x_axis(self, name: str) -> Iterable[float]:
        yield from self._dictionary[name].x_ordered_values()

    def to_dataframe(self) -> pd.DataFrame:
        result = pd.DataFrame(columns=self.function_names())
        for name in self.function_names():
            for x in self.get_ordered_x_axis(name):
                result.loc[x, name] = self.get_function_y(name, x)
        result.sort_index()
        return result

    def get_union_of_all_xaxis(self) -> Iterable[float]:
        xaxis = set()
        for name in self.function_names():
            xaxis = xaxis.union(self._dictionary[name].x_unordered_values())
        return xaxis

    def get_function_number_of_points(self, name: str) -> int:
        return self._dictionary[name].number_of_points()

    def drop_all_points_after(self, x: float, x_included: bool = True):
        for name, f in self._dictionary.items():
            to_remove = set()
            for ax in f.x_ordered_values():
                if (ax > x) or (ax == x and x_included is True):
                    to_remove.add(ax)
            for p in to_remove:
                f.remove_point(p)

    def functions_share_same_xaxis(self) -> bool:
        xaxis = None
        for name, f in self.items():
            if xaxis is None:
                xaxis = set(f.x_unordered_values())
            else:
                other = set(f.x_unordered_values())
                if xaxis != other:
                    return False
        return True

    def get_ith_xvalue(self, name: str, index: int) -> float:
        return self._dictionary[name].get_ith_xvalue(index)

    def change_ith_x(self, x_index: int, new_value: float):
        for name in self.function_names():
            self._dictionary[name].change_ith_x(x_index, new_value)

    def max_of_function(self, name: str) -> float:
        return max(self._dictionary[name].y_unordered_value())

    def get_function_name_with_most_points(self) -> str:
        current_max = -1
        current_max_name = None
        for name in self.function_names():
            function_max = self.get_function(name).number_of_points()
            if function_max > current_max:
                current_max = function_max
                current_max_name = name
        if current_max_name is None:
            raise ValueError(f"computing max on empty dataframe!")
        return current_max_name


class DataFrameFunctionsDict(commons.SlottedClass, IFunctionsDict):
    """
    A class which saves the functions inside a single dataframe

    The dataframe is structured as follows: each function is represented by a column. the Column
    name is the function name. the x axis is the index of the dataframe.
    If a function does not have a y values associated to an xaxis, NAN is put instead.

    """

    __slots__ = ('_dataframe', )

    def __init__(self):
        super(DataFrameFunctionsDict, self).__init__()
        self._dataframe = pd.DataFrame()

    @classmethod
    def empty(cls, functions: Iterable[str], size: int) -> "DataFrameFunctionsDict":
        result = cls()

        data = np.ndarray((size, len(list(functions))))
        data.fill(np.NaN)
        result._dataframe = pd.DataFrame(
            data=np.NaN,
            columns=functions,
        )

        return result

    @classmethod
    def from_other(cls, other: "IFunctionsDict"):
        result = cls()
        result._dataframe = other.to_dataframe()
        return result

    @classmethod
    def from_dataframe(cls, other: pd.DataFrame):
        result = cls()
        result._dataframe = other
        return result

    def function_names(self) -> Iterable[str]:
        yield from self._dataframe.columns.values

    def functions(self) -> Iterable["IFunction2D"]:
        for name in self.function_names():
            yield self.get_function(name)

    def size(self) -> int:
        return self._dataframe.shape[1]

    def max_function_length(self) -> int:
        return max(self._dataframe.count(axis=0, numeric_only=True))

    def get_function(self, name: str) -> "IFunction2D":
        return SeriesFunction.from_dataframe(self._dataframe.loc[:, name])

    def set_function(self, name: str, f: "IFunction2D"):
        self._dataframe.join(f.to_dataframe(), how='outer')
        self._dataframe.sort_index(inplace=True)

    def remove_function(self, name: str):
        self._dataframe.drop([name], axis=1)

    def _number_of_rows(self) -> int:
        return self._dataframe.shape[0]

    def contains_function_point(self, name: str, x: float) -> bool:
        return np.isnan(self._dataframe.loc[x, name])

    def get_function_y(self, name: str, x: float) -> float:
        result = self._dataframe.loc[x, name]
        if np.isnan(result):
            raise KeyError(f"function {name} does not have a value on axis {x}")
        return result

    def update_function_point(self, name: str, x: float, y: float):
        # this will add NaN in the missing spot or add a new row
        self._dataframe.loc[x, name] = y
        # we may need to sort the index
        self._dataframe.sort_index(inplace=True)

    def remove_function_point(self, name: str, x: float):
        self._dataframe.loc[x, name] = np.NaN
        self._dataframe.dropna(how='all')

    def contains_function(self, name: str) -> bool:
        return name in self._dataframe.columns.values

    def get_ordered_x_axis(self, name: str) -> Iterable[float]:
        # TODO improve performances by caching xaxis of functions
        for x in self._dataframe.index:
            if not np.isnan(self._dataframe.loc[x, name]):
                yield x

    def to_dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def get_union_of_all_xaxis(self) -> Iterable[float]:
        yield from self._dataframe.index

    def get_function_number_of_points(self, name: str) -> int:
        return self._dataframe.loc[:, name].dropna().shape[0]

    def drop_all_points_after(self, x: float, x_included: bool = True):
        if x_included is False:
            raise NotImplementedError()
        self._dataframe.drop(self._dataframe.index[x:], inplace=True)

    def functions_share_same_xaxis(self) -> bool:
        return not self._dataframe.isnull().values.any()

    def get_ith_xvalue(self, name: str, index: int) -> float:
        for i, x in enumerate(self.get_ordered_x_axis(name)):
            if i == index:
                return x
        raise ValueError(f"in valid {index}!")

    def change_ith_x(self, x_index: int, new_value: float):
        old_value = self._dataframe.index[x_index]
        self._dataframe = self._dataframe.iloc[x_index].rename({old_value: new_value})

    def get_function_name_with_most_points(self) -> str:
        return self._dataframe.count(axis=0, numeric_only=True).idxmax()

    def max_of_function(self, name: str) -> float:
        return self._dataframe[name].max(skipna=True)


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
            raise KeyError(f"key {name} is not inside options (which are {list(self.options())})")
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options (which are {list(self.options())})")
        self.__dict__[name] = value


class AbstractTestingGlobalSettings(ITestingGlobalSettings, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingGlobalSettings.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractStuffUnderTest(IStuffUnderTest, StandardOptionDict, abc.ABC):

    def __init__(self):
        IStuffUnderTest.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestingEnvironment(ITestEnvironment, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestEnvironment.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestContext(ITestContext, abc.ABC):

    def __init__(self, ut: "IStuffUnderTest", te: "ITestEnvironment"):
        ITestContext.__init__(self, ut=ut, te=te)

    @abc.abstractmethod
    @property
    def ut(self) -> "IStuffUnderTest":
        """
        Return the stuff under test

        This abstract property exists because in this way IDE (like PyCharm) can detect an abstract method to implement.
        In this way the developer can remember to implement this property. Furthermore, this is an opportunity for
        the developer to specify the type of IStuffUnderTest for her purpose. In the context of sorting algorithm,
        The developer can implement the property as follows:

        ```
        @property
        def te(self) -> "SortAlgorithm":
            return self._ut
        ```

        The implementation is normally just `return self._ut`: the important piece here is the annotation of the return
        type; this allows IDE (e.g., PyCharm) to help the developer when coding the tests

        :return: the test enviroment
        """
        pass

    @abc.abstractmethod
    @property
    def te(self) -> "ITestEnvironment":
        """
        Return the test environment

        This abstract property exists because in this way IDE (like PyCharm) can detect an abstract method to implement.
        In this way the developer can remember to implement this property. Furthermore, this is an opportunity for
        the developer to specify the type of ITestEnviroment for her purpose. In the context of sorting algorithm,
        The developer can implement the property as follows:

        ```
        @property
        def te(self) -> "SortEnvironment":
            return self._te
        ```

        The implementation is normally just `return self._te`: the important piece here is the annotation of the return
        type; this allows IDE (e.g., PyCharm) to help the developer when coding the tests

        :return: the test enviroment
        """
        pass


class AbstractStuffUnderTestMask(IStuffUnderTestMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        IStuffUnderTestMask.__init__(self)


class AbstractTestEnvironmentMask(ITestEnvironmentMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestEnvironment.__init__(self)


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

