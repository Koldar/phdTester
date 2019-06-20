from typing import Iterable, Tuple, Dict

from phdTester import commons
from phdTester.common_types import SlottedClass
from phdTester.model_interfaces import IFunctionsDict

import pandas as pd
import numpy as np


# class Function2D(SlottedClass, IFunction2D):
#     """
#     Represents a function y=f(x). The function is merely a set of 2D points, so it's more like a mapping.
#     Functions have no names
#     """
#
#     __slots__ = ('_function', '_sortedx', '_sortedx_valid')
#
#     def __init__(self):
#         super().__init__()
#         self._function = {}
#         self._sortedx = []
#         """
#         A list of sorted x values. Introduced to cache the order to the x values
#         """
#         self._sortedx_valid: bool = False
#         """
#         true if the field _sortedx is actually representing the sorted set of _function, false otherwise
#         """
#
#     @classmethod
#     def from_xy(cls, x: Iterable[float], y: Iterable[float]) -> "IFunction2D":
#         """
#         Create a new function from 2 lists of the same length
#         :param x: the x values
#         :param y: the y values
#         :return: a new function
#         """
#         result = cls()
#         for x, y in zip(x, y):
#             result.update_point(x, y)
#         return result
#
#     def update_point(self, x: float, y: float):
#         """
#         adds a point in the function.
#         If the value was already present the old value is overwritten
#
#         :param x: the x vlaue to add
#         :param y: the y value to add
#         """
#         self._function[x] = y
#         self._sortedx_valid = False
#
#     def remove_point(self, x: float):
#         self._sortedx_valid = False
#         del self._function[x]
#
#     def get_y(self, x: float) -> float:
#         """
#
#         :param x: the x value whose y value we need to fetch
#         :return: the y value associated to the x value
#         """
#         return self._function[x]
#
#     def number_of_points(self) -> int:
#         return len(self._function)
#
#     def x_unordered_values(self) -> Iterable[float]:
#         """
#
#         :return: iterable of x values. Order is **not** garantueed
#         """
#         return self._function.keys()
#
#     def change_ith_x(self, x_index: int, new_value: float):
#         super(Function2D, self).change_ith_x(x_index, new_value)
#         self._sortedx_valid = False
#
#     def change_x(self, old_x: float, new_x: float, overwrite: bool = False):
#         super(Function2D, self).change_x(old_x, new_x, overwrite)
#         self._sortedx_valid = False
#
#     def x_ordered_values(self) -> Iterable[float]:
#         """
#
#         :return: iterable of x values. Order goes from the lowest till the greatest
#         """
#         if not self._sortedx_valid:
#             self._sortedx = list(sorted(self._function.keys()))
#             self._sortedx_valid = True
#         return self._sortedx
#
#     def y_unordered_value(self) -> Iterable[float]:
#         """
#
#         :return: iterable of y values. Order is **not** garantueed
#         """
#         return self._function.values()
#
#     def xy_unordered_values(self) -> Iterable[Tuple[float, float]]:
#         """
#
#         :return: iterable of pair os x,y. Order is **not** garantueed
#         """
#         return self._function.items()
#
#     def to_series(self) -> pd.Series:
#         return pd.Series(self._function)
#
#     def to_dataframe(self) -> pd.DataFrame:
#         return pd.DataFrame(self.to_series())
#
#
# class SeriesFunction(SlottedClass, IFunction2D):
#
#     __slots__ = ('_series', '_max_x')
#
#     def __init__(self):
#         super(SeriesFunction, self).__init__()
#         self._series = pd.Series([])
#         self._max_x = float('-inf')
#
#
#     @classmethod
#     def from_dataframe(cls, df: pd.DataFrame) -> "SeriesFunction":
#         result = cls()
#
#         result._series = pd.Series(df)
#         result._max_x = result._series.max()
#
#         return result
#
#     def update_point(self, x: float, y: float):
#         self._series[x] = y
#         if x > self._max_x:
#             self._max_x = x
#         else:
#             # the index may not be sorted anymore. We need to sort it back
#             self._series.sort_index(inplace=True)
#
#     def remove_point(self, x: float):
#         del self._series[x]
#         if len(self._series) > 0:
#             if x == self._max_x:
#                 self._max_x = self._series.index[self._series.idxmax()]
#         else:
#             self._max_x = float('-inf')
#
#     def get_y(self, x: float) -> float:
#         return self._series[x]
#
#     def number_of_points(self) -> int:
#         return len(self._series)
#
#     def x_unordered_values(self) -> Iterable[float]:
#         return self._series.index
#
#     def x_ordered_values(self):
#         return self._series.index
#
#     def y_unordered_value(self) -> Iterable[float]:
#         return self._series.values
#
#     def to_series(self) -> pd.Series:
#         return self._series
#
#     def to_dataframe(self) -> pd.DataFrame:
#         return pd.DataFrame(self._series)


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


# class PandasFunction(SlottedClass, IFunction2D):
#
#     __slots__ = ('df', )
#
#     def __init__(self):
#         super().__init__()
#         self.df = pd.DataFrame(columns=['x', 'y'])
#         self.df.set_index('x', inplace=True)
#
#     def update_point(self, x: float, y: float):
#         # FIXME this is called lots of time and it slow down application
#         self.df.loc[x] = [y]
#
#     def has_x_value(self, x: float) -> bool:
#         return x in self.df.index
#
#     def remove_point(self, x: float):
#         self.df.drop(x, axis=0, inplace=True)
#
#     def get_y(self, x: float) -> float:
#         return float(self.df.loc[x]['y'])
#
#     def number_of_points(self) -> int:
#         return self.df.shape[0]
#
#     def x_unordered_values(self) -> Iterable[float]:
#         return iter(self.df.index)
#
#     def y_unordered_value(self) -> Iterable[float]:
#         return self.df.loc[:, 'y']
#
#     def to_series(self) -> pd.Series:
#         return self.df.loc[:, 'y']
#
#     def to_dataframe(self) -> pd.DataFrame:
#         return self.df


# class StandardFunctionsDict(SlottedClass, IFunctionsDict):
#     """
#     A class which saves the different functions inside a dict
#     """
#
#     __slots__ = ("_dictionary", )
#
#     def __init__(self):
#         super().__init__()
#         self._dictionary: Dict[str, "IFunction2D"] = {}
#
#     def function_names(self) -> Iterable[str]:
#         yield from self._dictionary.keys()
#
#     def functions(self) -> Iterable["IFunction2D"]:
#         yield from self._dictionary.values()
#
#     def size(self) -> int:
#         return len(self._dictionary)
#
#     def max_function_length(self) -> int:
#         return max(map(lambda name: self.get_function(name).number_of_points(), self.function_names()))
#
#     def get_function(self, name: str) -> "IFunction2D":
#         return self._dictionary[name]
#
#     def set_function(self, name, f: "IFunction2D"):
#         self._dictionary[name] = f
#
#     def remove_function(self, name: str):
#         del self._dictionary[name]
#
#     def contains_function_point(self, name: str, x: float) -> bool:
#         return self._dictionary[name].has_x_value(x)
#
#     def get_function_y(self, name: str, x: float) -> float:
#         return self._dictionary[name].get_y(x)
#
#     def update_function_point(self, name: str, x: float, y: float):
#         self._dictionary[name].update_point(x, y)
#
#     def remove_function_point(self, name: str, x: float):
#         self._dictionary[name].remove_point(x)
#
#     def contains_function(self, name: str) -> bool:
#         return name in self._dictionary
#
#     def get_ordered_x_axis(self, name: str) -> Iterable[float]:
#         yield from self._dictionary[name].x_ordered_values()
#
#     def to_dataframe(self) -> pd.DataFrame:
#         result = pd.DataFrame(columns=self.function_names())
#         for name in self.function_names():
#             for x in self.get_ordered_x_axis(name):
#                 result.loc[x, name] = self.get_function_y(name, x)
#         result.sort_index()
#         return result
#
#     def get_union_of_all_xaxis(self) -> Iterable[float]:
#         xaxis = set()
#         for name in self.function_names():
#             xaxis = xaxis.union(self._dictionary[name].x_unordered_values())
#         return xaxis
#
#     def get_function_number_of_points(self, name: str) -> int:
#         return self._dictionary[name].number_of_points()
#
#     def drop_all_points_after(self, x: float, x_included: bool = True):
#         for name, f in self._dictionary.items():
#             to_remove = set()
#             for ax in f.x_ordered_values():
#                 if (ax > x) or (ax == x and x_included is True):
#                     to_remove.add(ax)
#             for p in to_remove:
#                 f.remove_point(p)
#
#     def functions_share_same_xaxis(self) -> bool:
#         xaxis = None
#         for name, f in self.items():
#             if xaxis is None:
#                 xaxis = set(f.x_unordered_values())
#             else:
#                 other = set(f.x_unordered_values())
#                 if xaxis != other:
#                     return False
#         return True
#
#     def get_ith_xvalue(self, name: str, index: int) -> float:
#         return self._dictionary[name].get_ith_xvalue(index)
#
#     def change_ith_x(self, x_index: int, new_value: float):
#         for name in self.function_names():
#             self._dictionary[name].change_ith_x(x_index, new_value)
#
#     def max_of_function(self, name: str) -> float:
#         return max(self._dictionary[name].y_unordered_value())
#
#     def get_function_name_with_most_points(self) -> str:
#         current_max = -1
#         current_max_name = None
#         for name in self.function_names():
#             function_max = self.get_function(name).number_of_points()
#             if function_max > current_max:
#                 current_max = function_max
#                 current_max_name = name
#         if current_max_name is None:
#             raise ValueError(f"computing max on empty dataframe!")
#         return current_max_name


class DataFrameFunctionsDict(SlottedClass, IFunctionsDict):
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

    @staticmethod
    def create_dataframe_empty() -> pd.DataFrame:
        result = pd.DataFrame().astype(np.float32)
        result.index = result.index.astype(np.float32)
        return result

    def function_names(self) -> Iterable[str]:
        yield from self._dataframe.columns.values

    # TODO remove
    # def functions(self) -> Iterable["IFunction2D"]:
    #     for name in self.function_names():
    #         yield self.get_function(name)

    def size(self) -> int:
        return self._dataframe.shape[1]

    def max_function_length(self) -> int:
        return max(self._dataframe.count(axis=0, numeric_only=True))

    def xaxis(self) -> Iterable[float]:
        yield from sorted(self._dataframe.index)

    #TODO remove
    # def get_function(self, name: str) -> "IFunction2D":
    #     return SeriesFunction.from_dataframe(self._dataframe.loc[:, name])

    #TODO remove
    # def set_function(self, name: str, f: "IFunction2D"):
    #     self._dataframe.join(f.to_dataframe(), how='outer')
    #     self._dataframe.sort_index(inplace=True)

    def remove_function(self, name: str):
        self._dataframe.drop([name], axis=1, inplace=True)

    def _number_of_rows(self) -> int:
        return self._dataframe.shape[0]

    def contains_function_point(self, name: str, x: float) -> bool:
        return not np.isnan(self._dataframe.loc[x, name])

    def get_function_y(self, name: str, x: float) -> float:
        result = self._dataframe.loc[x, name]
        if np.isnan(result):
            raise KeyError(f"function {name} does not have a value on axis {x}")
        return result

    def get_first_x(self, name: str) -> float:
        return self._dataframe.index[0]

    def get_first_y(self, name: str) -> float:
        return self._dataframe.iloc[0][name]

    def get_last_y(self, name: str) -> float:
        return self._dataframe.iloc[-1][name]

    def get_first_valid_y(self, name: str) -> float:
        return self._dataframe.loc[self._dataframe.get_first_valid_x(), name]

    def get_first_valid_x(self, name: str) -> float:
        return self._dataframe[name].first_valid_index()

    def get_last_valid_y(self, name: str) -> float:
        return self._dataframe.loc[self._dataframe.get_last_valid_x(), name]

    def get_last_valid_x(self, name: str) -> float:
        return self._dataframe[name].last_valid_index()

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

    def items(self) -> Iterable[Tuple[str, "pd.Series"]]:
        for column in self._dataframe:
            yield column, self._dataframe[column].dropna(axis=0, inplace=False)

    def get_statistics(self, name: str, lower_percentile: float = 0.25, upper_percentile: float = 0.75) -> BoxData:
        result = self._dataframe[name].describe()
        return BoxData(
            count=result['count'],
            min=result['min'],
            max=result['max'],
            lower_percentile=result[f'{lower_percentile * 100}%'],
            upper_percentile=result[f'{upper_percentile * 100}%'],
            median=result['50%'],
            mean=result['mean'],
            std=result['std'],
        )

    def replace_invalid_values(self, to_value: float):
        self._dataframe.replace([np.inf, -np.inf], np.nan, inplace=True)
        self._dataframe.fillna(value=to_value, inplace=True)

