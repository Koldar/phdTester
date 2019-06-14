import abc
import logging
import math
import os
from typing import Dict, Callable, Union, Tuple, Any, Optional, Set, List, Iterable

import numpy as np
import pandas as pd
import dask.dataframe as dd

from phdTester import commons, common_types
from phdTester.common_types import SlottedClass
from phdTester.curve_changers.shared_curves_changers import AbstractTransformX, AbstractTransformY
from phdTester.default_models import UpperBoundSlotValueFetcher
from phdTester.functions import DataFrameFunctionsDict
from phdTester.image_computer import aggregators
from phdTester.model_interfaces import ICurvesChanger, ITestContext, IFunctionsDict, XAxisStatus, \
    ITestContextMask, ISlotValueFetcher


class StandardTransformX(AbstractTransformX):
    """
    Transform each xaxis of each curve passed to this changes

    In this curve changer, every x value of every function will be put as input inside a mapping function and a new x
    value will be generated.

    For example if you have
    ```
    (0,3) (1,4) (2,5)
    ```

    you can pass x_new = x_old + 3
    to obtain:
    ```
    (3,3) (4,4) (5,5)
    ```

    :note: this curve changer is likely to be very slow for big IFunctionDict
    """

    def __init__(self, mapping: Callable[[str, float, float], float]):
        """

        :param mapping: the mapping function. the parameters are the following:
         - the name of the function
         - the x value (that will be replaced)
         - the y value the function `name` has at value `x`
         - the return value is the new x value
        """
        AbstractTransformX.__init__(self)
        self.__mapping = mapping

    def _mapping(self, function_name: str, x_value: float, y_value: float) -> float:
        return self.__mapping(function_name, x_value, y_value)


class StandardTransformY(AbstractTransformY):
    """
    Transform all y values into something else

    this curve changer is slow, since it needs to scan all the values in the IFunctionDict
    """

    def __init__(self, mapping: Callable[[str, float, float], float]):
        AbstractTransformY.__init__(self)
        self.mapping = mapping

    def _mapping(self, name: str, x: float, y: float) -> float:
        return self.mapping(name, x, y)


class ReplaceFirstNaNValues(ICurvesChanger):
    """
    For each function it replace NaN values up until it finds a non NaN value.


    For example
    ```
    (0, Nan) (1, Nan) (2, 5) (3, Nan) (4, 10)
    ```
    Will be replaced with (assuming vlaue is 10):
    ```
    (0, 10) (1, 10) (2, 5) (3, Nan) (4, 10)
    ```

    """

    def __init__(self, value: float):
        self.__value = value

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df = curves.to_dataframe()
        for name in curves.function_names():
            first_non_nan_index = df[name].first_valid_index()
            if first_non_nan_index is None:
                # there are no NaN numbers in the series
                continue

            df.loc[df.index < first_non_nan_index, [name]] = self.__value
        return XAxisStatus.UNKNOWN, curves


class ReplaceTailNaNValues(ICurvesChanger):
    """
    For each function it replace NaN values from the last non NaN value till the end.


    For example
    ```
    (0, Nan) (1, Nan) (2, 5) (3, Nan) (4, 10) (5, Nan)
    ```
    Will be replaced with (assuming vlaue is 10):
    ```
    (0, Nan) (1, Nan) (2, 5) (3, Nan) (4, 10) (5, 10)
    ```

    """

    def __init__(self, value: float):
        self.__value = value

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df = curves.to_dataframe()
        for name in curves.function_names():
            last_non_nan_index = df[name].last_valid_index()
            if last_non_nan_index is None:
                # there are no NaN numbers in the series
                continue

            df.loc[df.index > last_non_nan_index, [name]] = self.__value
        return XAxisStatus.UNKNOWN, curves


class ReplaceNanWithPreviousValue(ICurvesChanger):
    """
    For each function it replace NaN values with the previous non NaN value.
    An error is generated if there is no previous non NaN value


    For example
    ```
    (0, 6) (1, Nan) (2, 5) (3, Nan) (4, 10) (5, Nan)
    ```
    Will be replaced with (assuming vlaue is 10):
    ```
    (0, 6) (1, 6) (2, 5) (3, 5) (4, 10) (5, 10)
    ```

    """

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        for name in curves.function_names():
            if np.isnan(curves.get_first_y(name)):
                raise ValueError(f"function {name} starts with a NaN!")

        curves.to_dataframe().fillna(method='ffill', inplace=True)

        return XAxisStatus.UNKNOWN, curves


class ReplaceNaNWithStops(ICurvesChanger):
    """
    This curve changer is pretty similar to ReplaceNanWithPreviousValue but if there is no first non NaN value
    for a function, we will use a default fixed one

    ```
    (0, Nan), (1, Nan) (2, 10) (3, Nan) (4, 5), (5, 4), (5, Nan) (6, Nan)
    ```
    will be converted to (assuming first and last character is 20):
    ```
    (0, 20), (1, 20), (2, 10), (3, 10), (4, 5), (5,4), (5, 4), (5, 4)
    ```
    """

    def __init__(self, first_value: float):
        self.__first_value = first_value

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        for name in curves.function_names():
            first_x = curves.get_first_x(name)
            if np.isnan(first_x):
                curves.update_function_point(name, first_x, self.__first_value)

        curves.to_dataframe().fillna(method='ffill', inplace=True)
        return XAxisStatus.SAME_X, curves


class RemapInvalidValues(ICurvesChanger):
    """
    Iterate over all the functions values. If it finds an invalid y value, it replaces it with a fixed value

    For example
    ```
    (0, 3) (1,inf) (2,4)
    ```
    is converted to (e.g. the fix value is 10):
    ```
    (0, 3) (1,10) (2,4)
    ```
    """

    def __init__(self, value):
        """

        :param value: the fixed value you want to use to convert infrinities and nan values
        """
        ICurvesChanger.__init__(self)
        self.__value = value

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        curves.replace_invalid_values(self.__value)
        return XAxisStatus.UNALTERED, curves


class SaveOnCsv(ICurvesChanger):
    """
    A curve changer which leave unaltered the functions but save the functions inside a csv
    """

    def __init__(self, csv_name: str):
        """

        :param csv_name: the absolute filename of the csv we want to create
        """
        self.__csv_name = csv_name

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        curves.to_dataframe().to_csv(self.__csv_name)
        return XAxisStatus.UNALTERED, curves


class AddCurve(ICurvesChanger):
    """
    Adds a curve based
    """

    def __init__(self, function_name: str, func: Callable[[int, float, "IFunctionsDict"], float]):
        self.__function_name = function_name
        self.__func = func

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        new_function = pd.Series(name=self.__function_name, index=curves.xaxis())
        for i, x in enumerate(curves.xaxis_ordered()):
            new_function[x] = self.__func(i, x, curves)

        df = curves.to_dataframe()
        df[self.__function_name] = new_function

        return XAxisStatus.UNKNOWN, curves


class Print(ICurvesChanger):
    """
    A change which simply log the curves via a function
    """

    def __init__(self, log_function: Callable[[str], Any]):
        """

        :param log_function: the function we will use to print the data. This function should accept a string
            and should log such string somewhere
        """
        self.log_function = log_function

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple[XAxisStatus, "IFunctionsDict"]:
        for name in curves.function_names():
            f = curves.get_function(name)
            self.log_function(f"name = {name}")
            self.log_function(f"x [size={f.number_of_points()}] = {list(commons.sequential_numbers(curves.get_ordered_x_axis(name)))}")
            self.log_function(f"f = {str(f)}")

        return XAxisStatus.UNALTERED, curves


class CheckSameXAxis(ICurvesChanger):
    """
    curve changer which checks if all the functions share the same x axis

    If 2 functions in the IFunctionDict have 2 different x axis, then the function generates an error
    """

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple[XAxisStatus, "IFunctionsDict"]:
        if not curves.functions_share_same_xaxis():
            xaxis = None
            xaxis_function_name = None
            for name, f in curves.items():
                if xaxis is None:
                    xaxis = set(f.index)
                    xaxis_function_name = name
                else:
                    other = set(f.index)
                    if xaxis != other:
                        raise ValueError(f"""X axis mismatch!
                            f name = {xaxis_function_name}
                            |xaxis_f| = {len(xaxis)}
                            g name = {name}
                            |xaxis_g| = {len(other)}

                            xaxis_f / xaxis_g (sorted) = {sorted(xaxis.difference(other))}
                            xaxis_g / xaxis_f (sorted) = {sorted(other.difference(xaxis))}""")
        return XAxisStatus.SAME_X, curves


class CheckNoNaN(ICurvesChanger):
    """
    Check that no curve has NaN. Raise an error otherwise
    """

    def require_same_xaxis(self) -> bool:
        return True

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df = curves.to_dataframe()
        if df.isnull().values.any():
            raise ValueError(f"a cell in curves is NaN!")
        return XAxisStatus.UNALTERED, curves


class CheckNoInvalidNumbers(ICurvesChanger):
    """
    Check that no curve has invalid numbers. Raise an error otherwise

    The invalid characters are the following:
     - Nan;
     - plus infinite;
     - negative infinite;
    """

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df = curves.to_dataframe()
        ddf: dd.DataFrame = dd.from_pandas(df, npartitions=os.cpu_count())
        if ddf.mask(np.isnan(ddf) | np.isinf(ddf)).any().compute():
            raise ValueError(f"a cell in curves is either NaN, +infinite or -infinite!")
        return XAxisStatus.UNALTERED, curves


class ReplaceAllWith(ICurvesChanger):

    def __init__(self, old_value: float, new_value: float):
        self.__old_value = old_value
        self.__new_value = new_value

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df = curves.to_dataframe()
        ddf = dd.from_pandas(df, npartitions=os.cpu_count())
        df = ddf.mask(ddf == self.__old_value, self.__new_value).compute()
        return XAxisStatus.UNKNOWN, DataFrameFunctionsDict.from_dataframe(df)


class RemoveSmallFunction(SlottedClass, ICurvesChanger):
    """
    A changer that removes curves which maximum never go up a certain value
    """

    __slots__ = ('__threshold', '__threshold_included', )

    def __init__(self, threshold: float, threshold_included: bool = False):
        self.__threshold = threshold
        self.__threshold_included = threshold_included

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple[XAxisStatus, "IFunctionsDict"]:

        for name in curves.function_names():
            m = curves.max_of_function(name)
            if not((m > self.__threshold) or (math.isclose(m, self.__threshold) and self.__threshold_included is True)):
                curves.remove_function(name)

        return XAxisStatus.UNALTERED, curves


class SortAll(ICurvesChanger):
    """
    The changer picks all the curves and just sort each cof them monotonically independently

    This will of course destroy all the relation between them. This can be used to generate a **cactus plot**
    """

    def __init__(self):
        ICurvesChanger.__init__(self)

    def require_same_xaxis(self) -> bool:
        return True

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        df = curves.to_dataframe()
        df = df.apply(lambda x: x.sort_values().values)
        return DataFrameFunctionsDict.from_dataframe(df)


class QuantizeXAxis(ICurvesChanger):
    """
    Discretize the x axis in a finite number of values

    Assume you have 3 curves over time in seconds, e.g.:

     - A <0.10,3> <1.10,3> <2.30, 3>
     - B <0.05,4> <1.11,4> <2.62, 4>
     - C <0.35,5> <1.23,5> <2.43, 5>

    These 3 plots are over 3 different X axis. To be able to plot them, you need to have the same axis.
    This curve changer quantize the x axis in slots and then group the slots together. For example we can choose to
    quantize the time in seconds, hence:

     - first point of A,B and C goes into the first time slot (form 0.0s to 0.99s);
     - second point of A,B and C goes into the second time slot (form 1.0s to 1.99s);
     - third point of A,B and C goes into the third time slot (form 2.0s to 2.99s);

    If several points of the same curve goes into the same slot, they will be merged with an aggregator.
    If a function has no points in a quantum, we will give it the value "NaN"
    """

    def __init__(self, quantization_levels: List[float], merge_method: str, slot_value: "ISlotValueFetcher" = None):
        """
        Initialize the quantization

        :param quantization_levels: represents the quantization step we need to apply. You can set it in 2 ways.
            First by listing the quantization level via a list (e.g., [1, 100, 500, 700]): so, if x=50, the quantization
            level will be (1,100). An error is thrown if no quantization level is found (e.g., x=1000). A more robust
            approach involve using a passing a lambda which has the following sigbnature:
             - input x: the x axis value to quantize;
             - output 1: the start value of the quantization level containing x;
             - output 2: the end value of the quantization level containing x;
            You can use IQuantizer class to implement the callable if you want
        :param aggregator: aggregator used to aggregate values which end up having the same x value
        :param slot_value: a function used to convert hte quantization level in a number. The function signature is
            the following one:
             - input 1: the x axis value that belongs to a certain quantization level
             - input 2: the lower bound x value of the quantization level
             - input 3: the upper bound x value of the quantization level
             - output: the number which is the new x value of the function instead of input 1.
            If not specified, the function will always return input 3.
        """
        ICurvesChanger.__init__(self)

        self.__quantization_levels = quantization_levels
        self.__merge_method = merge_method
        self.__slot_value = slot_value or UpperBoundSlotValueFetcher()

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple[XAxisStatus, "IFunctionsDict"]:
        df = curves.to_dataframe()

        # see https://stackoverflow.com/a/52872853/1887602
        # see https://stackoverflow.com/a/33761120/1887602
        grouped = df.groupby(pd.cut(
            x=df.index,
            bins=pd.IntervalIndex.from_tuples(list(commons.get_interval_ranges(self.__quantization_levels))),
        ))
        # groups index is composed by intervals

        if self.__merge_method == 'min':
            df = grouped.min()
        elif self.__merge_method == 'max':
            df = grouped.max()
        else:
            raise ValueError(f"invalid value {self.__merge_method}! Only min is accepted!")

        # see https://stackoverflow.com/a/30590280/1887602
        # see https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Interval.html

        # replace the index: instead of using intervals we use a derivation of them
        df.index = df.index.map(lambda interval: self.__slot_value.fetch(interval.left, interval.right, False, True))
        df.index = pd.to_numeric(df.index)

        # this may leave NaN inside the functions (if in the quantization level the function is not defined)

        # it's unknown because a function may be defined over every quantization level while another one maybe defined
        # only over a subset of it. So we cannot be sure
        return XAxisStatus.UNKNOWN, DataFrameFunctionsDict.from_dataframe(df)


class StatisticsOfFunctionsPerX(ICurvesChanger):
    """
    Generates statistics of several plots which can be grouped

    Assume you have 9 plots which can be grouped 3 by 3. For example:

    A1 (0,3), (1,4), (2,5)
    A2 (0,13), (1,14), (2,15)
    A3 (0,23), (1,24), (2,25)

    B1 (0,31), (1,41), (2,51)
    B2 (0,32), (1,42), (2,52)
    B3 (0,33), (1,43), (2,53)

    C1 (0,43), (1,51), (2,51)
    C2 (0,46), (1,56), (2,50)
    C3 (0,45), (1,58), (2,59)

    All the plots shares the same x axis.
    What you want is to group the 9 plots in 3 groups:
     - A1,A2,A3
     - B1,B2,B3
     - C1,C2,C3

    Then For each group you want to obtain statistical metrics for each x axis value.
    For example, in group A you want to have mean and median for x=0, x=1, x=2.

    Note that for each group for each x value you obtain a list of numbers (hence you can
    compute statistical indices)
    """

    class IFunctionGrouper(abc.ABC):

        @abc.abstractmethod
        def get_group(self, function_name: str, test_context: "ITestContext") -> str:
            pass

    class DefaultFunctionGroup(IFunctionGrouper):

        def get_group(self, function_name: str, test_context: "ITestContext") -> str:
            return test_context.ut.get_label()

    def __init__(self, test_context_template: "ITestContext", function_grouper: DefaultFunctionGroup = None, lower_percentile: float = 0.25, upper_percentile: float = 0.75, include_infinities: bool = False, colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '='):
        self.__test_context_template = test_context_template
        self.__lower_percentile = lower_percentile
        self.__upper_percentile = upper_percentile
        self.__function_grouper = function_grouper or StatisticsOfFunctionsPerX.DefaultFunctionGroup()
        self.__include_infinities = include_infinities
        self.__colon = colon
        self.__pipe = pipe
        self.__underscore = underscore
        self.__equal = equal

    def require_same_xaxis(self) -> bool:
        return True

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        df: pd.DataFrame = curves.to_dataframe()

        # maps function_grouper output with the list of function names which has generated such key
        columns_mapping: Dict[str, List[str]] = {}
        for name in curves.function_names():
            tc = self.__test_context_template.clone()
            tc.populate_from_ks001_string_on_index(
                index=0,
                string=name,
                colon=self.__colon,
                pipe=self.__pipe,
                underscore=self.__underscore,
                equal=self.__equal,
            )
            key = self.__function_grouper.get_group(name, tc)
            if key not in columns_mapping:
                columns_mapping[key] = []
            columns_mapping[key].append(name)

        # each value represent the subset of dataframe to generate
        result: DataFrameFunctionsDict = DataFrameFunctionsDict()
        df_result = result.to_dataframe()
        for group_name, function_names in columns_mapping.items():
            with_infinities = df[function_names]\
                .transpose()\
                .describe(percentiles=[self.__lower_percentile, 0.5, self.__upper_percentile]) \
                .transpose()

            df_result[f"{group_name} count"] = with_infinities['count']
            df_result[f"{group_name} min"] = with_infinities['min']
            df_result[f"{group_name} max"] = with_infinities['max']
            df_result[f"{group_name} {int(self.__lower_percentile * 100)}%"] = with_infinities[f'{int(self.__lower_percentile * 100)}%']
            df_result[f"{group_name} {int(self.__upper_percentile * 100)}%"] = with_infinities[f'{int(self.__upper_percentile * 100)}%']
            df_result[f"{group_name} median"] = with_infinities[f'50%']
            df_result[f"{group_name} mean"] = with_infinities[f'mean']

            if self.__include_infinities:
                without_infinities = df[function_names]\
                    .replace([np.inf, -np.inf], np.nan)\
                    .transpose()\
                    .describe(percentiles=[self.__lower_percentile, 0.5, self.__upper_percentile]) \
                    .transpose()

                df_result[f"{group_name} count (no inf)"] = without_infinities['count']
                df_result[f"{group_name} min (no inf)"] = without_infinities['min']
                df_result[f"{group_name} max (no inf)"] = without_infinities['max']
                df_result[f"{group_name} {int(self.__lower_percentile * 100)}% (no inf)"] = without_infinities[f'{int(self.__lower_percentile * 100)}%']
                df_result[f"{group_name} {int(self.__upper_percentile* 100)}% (no inf)"] = without_infinities[f'{int(self.__upper_percentile * 100)}%']
                df_result[f"{group_name} median (no inf)"] = without_infinities[f'50%']
                df_result[f"{group_name} mean (no inf)"] = without_infinities[f'mean']

        return XAxisStatus.UNALTERED, result


class Identity(ICurvesChanger):
    """
    A changer that does nothing
    """

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        return curves

    def require_same_xaxis(self) -> bool:
        return False





















# class AbstractSingleTransform(ICurvesChanger, abc.ABC):
#     """
#     A curve changer which map a function into another one. Basically it's a map over a single function
#     """
#
#     def __init__(self, name: str, new_name: str = None):
#         ICurvesChanger.__init__(self)
#         self.name = name
#         self.new_name: Optional[str] = new_name
#
#     @abc.abstractmethod
#     def _mapping(self, x: float, y: float) -> float:
#         pass
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         f = SeriesFunction()
#         for x, y in curves[self.name].xy_unordered_values():
#             f[x] = self._mapping(x, curves.get_function_y(self.name, x))
#
#         del curves[self.name]
#         name = self.new_name if self.new_name is not None else self.name
#         curves.set_function(name, f)
#
#         return curves
#
#
# class SimpleTransform(AbstractSingleTransform):
#
#     def __init__(self, name: str, mapping: Callable[[float, float], float], new_name: str = None):
#         AbstractSingleTransform.__init__(self, name, new_name=new_name)
#         self.mapping = mapping
#
#     def _mapping(self, x: float, y: float) -> float:
#         return self.mapping(x, y)
#
#
# class AbstractSyntheticFunction(ICurvesChanger, abc.ABC):
#     """
#     A curve changer which adds a new function in the array available. Used to generate derived functions
#     """
#
#     def __init__(self, name: str):
#         ICurvesChanger.__init__(self)
#         self.name = name
#
#     @abc.abstractmethod
#     def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
#         pass
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         for x in list(curves.values())[0].x_ordered_values():
#             curves.update_function_point(self.name, x, self._compute_f(x, curves))
#         return curves
#
#
# class SyntheticFunction(AbstractSyntheticFunction):
#     """
#     A curve changer which adds a new function in the array available. Used to generate derived functions
#     """
#
#     def __init__(self, name: str, f: Callable[[float, "IFunctionsDict"], float]):
#         AbstractSyntheticFunction.__init__(self, name)
#         self.f = f
#
#     def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
#         return self.f(x, curves)
#
#
# class SyntheticCount(AbstractSyntheticFunction):
#     """
#     Adds a synthetic function whose y associated to a x is the number of functions applied to x satisfying a particular criterion
#     """
#
#     def __init__(self, name: str, criterion: Callable[[str, float, float], bool]):
#         AbstractSyntheticFunction.__init__(self, name)
#         self.criterion = criterion
#
#     def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
#         result = 0
#         for name, f in curves.items():
#             if self.criterion(name, x, f[x]):
#                 result += 1
#         return result
#
#
# class SyntheticPercentage(SyntheticCount):
#     """
#     Adds a synthetic function whose y associated to a x is the percentage of functions applied to x satisfying a particular criterion.
#
#     The percentage is expressed between [0,1]
#     """
#
#     def __init__(self, name: str, criterion: Callable[[str, float, float], bool]):
#         SyntheticCount.__init__(self, name, criterion)
#
#     def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
#         result = 0
#         for name, f in curves.items():
#             if self.criterion(name, x, f[x]):
#                 result += 1
#         return result/len(curves)
#
#
#
#
#
#
#
#
#
#
#
# class UseValueToFillCurve(ICurvesChanger):
#     """
#     Fill the values not existing of every function with a specified value
#
#     It may happen that, during the computation of a function, some curve do not have some values (for example because
#     the stuff under test required too much time and it was summarly killed). If this is the case this changer will
#     fill this non-existing values with a default value
#     """
#
#     def __init__(self, value: Union[float, int]):
#         ICurvesChanger.__init__(self)
#         self.value = value
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         shared_xaxis = curves.get_union_of_all_xaxis()
#
#         for name in curves.function_names():
#             for x in shared_xaxis:
#                 if x not in curves.contains_function_point(name, x):
#                     curves.update_function_point(name, x, self.value)
#         return curves
#
#
# class RemoveSmallCurve(ICurvesChanger):
#     """
#     The changer will remove from the plotting curves which do not have a compliant number of points
#     """
#
#     def __init__(self, min_size: int = None, max_size: int = None):
#         """
#
#         :param min_size: the minimum amount of points needed to avoid being removed.
#             if the number of point is exactly `min_size` your curve **won't** be removed.
#         :param max_size: the maximum amount of points needed to avoid being removed.
#             if the number of point is exactly `min_size` your curve **won't** be removed.
#         """
#         ICurvesChanger.__init__(self)
#         self.min_size = min_size
#         self.max_size = max_size
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         for name in curves.function_names():
#             if self.min_size is not None and curves.get_function(name).number_of_points() < self.min_size:
#                 curves.remove_function(name)
#             if self.max_size is not None and curves.get_function(name).number_of_points() > self.max_size:
#                 curves.remove_function(name)
#
#         return curves
#
#
# class TruncateToLowestX(ICurvesChanger):
#     """
#     When plot have different x axis shared axis, you may need to truncate the longest one.
#
#     For example if 2 functions are
#
#     A = 1;03 2;06 3;14
#     B = 1;09 2;12 3;15 4;20; 5;30
#
#     You may want to truncate be to have the same values of A.
#
#     In order to work the functions can't have missing values. For example the changer won't work on these functions
#
#     A = 1;03 2;06 3;14
#     B = 1;09 3;15 4;20; 5;30
#     """
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         # we get the minimum length of the curve
#         min_length = min(map(lambda x: x.number_of_points(), curves.functions()))
#
#         # ok, truncate everything which is over min_length
#         curves.drop_all_points_after(min_length)
#
#         return curves
#
#
# class AbstractFunctionGroup(abc.ABC):
#     """
#     A data structure representing the data inside a group of function.
#
#     Data structure connected to :ref AbstractGrouper:
#     """
#
#     def __init__(self, name: str):
#         self.name = name
#
#     def get_name(self) -> str:
#         return self.name
#
#     @abc.abstractmethod
#     def add_function(self, name: str, curves: "IFunctionsDict"):
#         """
#         operation to perform to add a function inside the current group
#
#         :param name: name of the function to add
#         :param curves: dictioary of functions where the function is located. It is garantueed that this
#         dictionary contains a function of name `name`
#         :return:
#         """
#         pass
#
#     @abc.abstractmethod
#     def to_functions(self) -> "IFunctionsDict":
#         pass
#
#
# class AbstractGrouper(ICurvesChanger, abc.ABC):
#     """
#     From several curves, it groups them in some way. Then it expand each group into one or more function.
#
#     Sometimes when computing curver functions, you need to group different curves according to a specific criteria
#     and then generate, for each group, some other functions. This abstract curve changer let's you do that
#
#     """
#
#     def __init__(self):
#         ICurvesChanger.__init__(self)
#
#     @abc.abstractmethod
#     def _get_new_group_instance(self, group_name: str) -> "AbstractFunctionGroup":
#         """
#         Whenever we need to create a new group of functions, we call this function, initializing said new (empty) group
#
#         :param group_name: the name of the group to create
#         :return:  the new group initialized
#         """
#         pass
#
#     @abc.abstractmethod
#     def _get_group_name(self, i: int, name: str, curves: "IFunctionsDict") -> str:
#         """
#         Given a function we're considering, generate the name of the group which the function will belong to
#
#         Function sharing the same group name will belong to the group
#
#         :param i: i-th function we've encountered
#         :param name: name of the funciton `function1`
#         :param curves: the dictionaries of functions we used to retrieve the function
#         :return: name fo the group to attahc the function to
#         """
#         pass
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         groups: Dict[str, "AbstractFunctionGroup"] = {}
#         for i, (name, ) in enumerate(curves.function_names()):
#             group_name = self._get_group_name(i, name, curves)
#             if group_name not in groups:
#                 groups[group_name] = self._get_new_group_instance(group_name)
#             groups[group_name].add_function(name, curves)
#
#         # now we convert the groups into a "IFunctionsDict"
#         result = DataFrameFunctionsDict()
#         for name, group in groups.items():
#             for new_name, new_function in group.to_functions().items():
#                 if new_name in result:
#                     raise ValueError(f"function {new_name} cannot be added because is already present in the dictionary!")
#                 result.set_function(new_name, new_function)
#         return result
#
#
# class BoxPlotGroup(AbstractFunctionGroup):
#     """
#     A group that merges the functions within the same group and compute the statistical indices for boxplotting.
#
#     The statistical indices for boxplotting are:
#      - min
#      - 50th-xth percentile
#      - 50th+xth percentile
#      - median
#      - average
#
#      The functions are merged together as follows:
#      - if 2 functions have the same x value, the 2 y will concur to compute the statistical indices for the same "x"
#      value
#     """
#
#     def __init__(self, name: str, percentile_watched: int, ignore_infinites: bool, generate_plots_ignoring_infinities: bool):
#         AbstractFunctionGroup.__init__(self, name)
#         self.percentile_watched = percentile_watched
#         self.ignore_infinites = ignore_infinites
#         self.generate_plots_ignoring_infinities = generate_plots_ignoring_infinities
#         self.functions: "IFunctionsDict" = DataFrameFunctionsDict()
#
#     def add_function(self, name: str, curves: "IFunctionsDict"):
#         self.functions.set_function(name, curves.get_function(name))
#
#     def _create_boxplot_functions(self, df: pd.DataFrame, suffix: str) -> "IFunctionsDict":
#         result: "IFunctionsDict" = DataFrameFunctionsDict()
#
#         result.set_function(
#             f"{self.get_name()}_max{suffix}",
#             SeriesFunction.from_dataframe(df.max(axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_min{suffix}",
#             SeriesFunction.from_dataframe(df.min(axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_average{suffix}",
#             SeriesFunction.from_dataframe(df.mean(axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_percentile={self.percentile_watched}{suffix}",
#             SeriesFunction.from_dataframe(df.quantile(q=self.percentile_watched / 100., axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_percentile={100 - self.percentile_watched}{suffix}",
#             SeriesFunction.from_dataframe(df.quantile(q=((100 - self.percentile_watched) / 100.), axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_percentile=50{suffix}",
#             SeriesFunction.from_dataframe(df.median(axis=1))
#         )
#         result.set_function(
#             f"{self.get_name()}_n {suffix}",
#             SeriesFunction.from_dataframe(df.count(axis=1))
#         )
#
#         return result
#
#     def to_functions(self) -> "IFunctionsDict":
#         result: "IFunctionsDict" = DataFrameFunctionsDict()
#
#         df = pd.DataFrame(result.to_dataframe())  # enforce a copy
#
#         if self.generate_plots_ignoring_infinities:
#             # we generate 2 set of boxplots, one considering infinities and the other not considering them
#             with_infinities = self._create_boxplot_functions(df, "_withinfinities")
#             without_infinities = self._create_boxplot_functions(df.replace(np.inf, np.NaN), '_withoutinfinities')
#             result = with_infinities + without_infinities
#         elif self.ignore_infinites:
#             # by default dataframe operations ignore NaN. So we convert the infinities into Nan
#             df.replace(np.inf, np.NaN, inplace=True)
#             result = self._create_boxplot_functions(df, "_withoutinfinities")
#         else:
#             # ok we treat the data as is
#             result = self._create_boxplot_functions(df, "")
#
#         return result
#
#
# class BoxPlotGrouper(AbstractGrouper):
#     """
#     A grouper which groups functions according to `get_group_name_f`.
#
#     Then we compute statistical indices (relevant for box plot) for each `x` axis values for each group.
#     In other words, each group is
#     synthesized in some curve representing statistical metrics trends.
#     """
#
#     def __init__(self, get_group_name_f: Callable[[int, str, "IFunction2D"], str], percentile_watched: int,
#                  ignore_infinities: bool = False, generate_plots_ignoring_infinities: bool = False):
#         """
#
#         :param get_group_name_f: function defining the group name of a given function.
#              - first parameter is the index fo the function;
#              - second parameter is the function name
#              - third paramete is the function itself
#         :param percentile_watched: the percentile to watch. If you want to look for the 25th and 75th quantile, write 25
#         :param ignore_infinities: true if you want to ignore "infinite" values during the computation of the curves.
#             Is overwritten by generate_plots_ignoring_infinities
#         :param generate_plots_ignoring_infinities: if true, we will generate 2 sets of curves: the first set will
#         contain min,max, quantiles considering infinites values. The second set will contain min, max, qwuantiles ignoring
#         infinite values. Overrides ignore_infinites parameter.
#         """
#         AbstractGrouper.__init__(self)
#         self.get_group_name_f = get_group_name_f
#         self.percentile_watched = percentile_watched
#         self.ignore_infinities = ignore_infinities
#         self.generate_plots_ignoring_infinities = generate_plots_ignoring_infinities
#
#     def _get_new_group_instance(self, group_name: str) -> AbstractFunctionGroup:
#         return BoxPlotGroup(group_name,
#                             percentile_watched=self.percentile_watched,
#                             ignore_infinities=self.ignore_infinities,
#                             generate_plots_ignoring_infinities=self.generate_plots_ignoring_infinities,
#                             )
#
#     def _get_group_name(self, i: int, name: str, function1: IFunction2D) -> str:
#         # we assume name is a ks001 representation
#         return self.get_group_name_f(i, name, function1)
#
#
# class MergeCurvesWithSameStuffUnderTest(ICurvesChanger):
#
#     def __init__(self, name_to_test_context: Callable[[str], "ITestContext"], y_aggregator: aggregators.IAggregator):
#         ICurvesChanger.__init__(self)
#         self.y_aggregator = y_aggregator
#         self.name_to_test_context = name_to_test_context
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         result = DataFrameFunctionsDict()
#
#         xaxis = list(curves.values())[0].x_ordered_values()
#         for x in xaxis:
#             self.y_aggregator.reset()
#
#             for name in curves.function_names():
#                 # we assume the name of the function is a KS001 structure from where we can generate a test context
#                 tc = self.name_to_test_context(name)
#                 label = tc.ut.get_label()
#                 if label not in result:
#                     result[label] = SeriesFunction()
#
#                 previous_y = self.y_aggregator.aggregate(curves.get_function_y(name, x))
#                 result.update_function_point(name, x, previous_y)
#
#         return result
#
#
# class MergeCurves(ICurvesChanger):
#
#     def __init__(self, label: str, y_aggregator: aggregators.IAggregator):
#         ICurvesChanger.__init__(self)
#         self.y_aggregator = y_aggregator
#         self.label = label
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         result = DataFrameFunctionsDict()
#
#         for x in list(curves.values())[0].x_ordered_values():
#             self.y_aggregator.reset()
#             for name in curves.function_names():
#                 previous_y = self.y_aggregator.aggregate(curves.get_function_y(name, x))
#                 result.update_function_point(self.label, x, previous_y)
#         return result
#
#
#
#
#
# class AbstractFillCurve(ICurvesChanger, abc.ABC):
#
#     def _compute_max_length(self, curves: "IFunctionsDict") -> Tuple[str, int]:
#         return curves.get_function_name_with_most_points(), curves.max_function_length()
#
#     @abc.abstractmethod
#     def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
#         pass
#
#     @abc.abstractmethod
#     def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
#         pass
#
#     @abc.abstractmethod
#     def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Any:
#         pass
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         xaxis = list((curves.get_union_of_all_xaxis()))
#         xaxis_len = len(xaxis)
#         # max_f, max_length = self._compute_max_length(curves)
#
#         # logging.debug(f"maximum is {max_length}")
#
#         # logging.critical(f"xaxis of reference is (size= {len(list(curves[max_f].x_ordered_values()))}): {curves[max_f].x_ordered_values()}")
#         for name in curves.function_names():
#             if curves.get_function_number_of_points(name) < xaxis_len:
#                 value = self._handle_begin_function_misses_values(name, curves)
#                 for x in xaxis:
#                     if x not in curves.get_ordered_x_axis(name):
#                         value = self._handle_x_not_in_function(x, name, curves, value)
#                     else:
#                         value = self._handle_x_in_function(x, name, curves, value)
#
#         return curves
#
#
# class AbstractRepeatPreviousValueToFillCurve(AbstractFillCurve, abc.ABC):
#     """
#     If a function does not have a value on a specific x, we assigne to that x f[x-1    """
#
#     def __init__(self,):
#         AbstractFillCurve.__init__(self)
#
#     @abc.abstractmethod
#     def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
#         pass
#
#     def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Optional[float]) -> Optional[float]:
#         if value is None:
#             return self._handle_first_absent_value(x, function_name, curves)
#         else:
#             curves.update_function_point(function_name, x, value)
#             return curves.get_function_y(function_name, x)
#
#     def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Optional[float]) -> float:
#         return curves.get_function_y(function_name, x)
#
#     def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Optional[float]:
#         return None
#
#
# class RepeatPreviousValueOrSetOneToFillCurve(AbstractRepeatPreviousValueToFillCurve):
#     """
#     If a function does not have a value on a specific x, we assigne to that x f[x-1].
#     If the first value is the one which is absent, we simply assign it a given one.
#     """
#
#     def __init__(self):
#         AbstractFillCurve.__init__(self, )
#         self.first_x = set()
#         """
#         If the first values of the curves are absent, we keep track of them and as soon as we find an x sch it exists
#         an y value we fill all the values to the just got value
#         """
#
#     def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
#         self.first_x.add(x)
#         return None
#
#
# class RepeatPreviousValueOrFirstOneToFillCurve(AbstractRepeatPreviousValueToFillCurve):
#     """
#     If a function does not have a value on a specific x, we assigne to that x f[x-1].
#     If the first value is the one which is absent, we simply wait until a value is detected. Then we populate all
#     the missing values with the ewnly discovered one.
#     """
#
#     def __init__(self, value: float):
#         AbstractFillCurve.__init__(self, )
#         self.value = value
#
#     def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
#         curves.update_function_point(function_name, x, self.value)
#         return curves.get_function_y(function_name, x)
#
#
# class RepeatValueToFillCurve(AbstractFillCurve):
#
#     def __init__(self, value: float):
#         AbstractFillCurve.__init__(self)
#         self.value = value
#
#     def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Any:
#         return (False, )
#
#     def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
#         curves.update_function_point(function_name, x, self.value)
#         return (True, )
#
#     def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: "Any") -> "Any":
#         if value[0]:
#             raise ValueError(f"detected a x {x} in function {function_name} which is not associated with a y value, but before it there was a x value associate to an y!")
#         return (value[0], )
#
#
# class RepeatEndToFillCurve(AbstractFillCurve):
#     """
#     Fill the values not existing of every function with the last detected value
#
#     It may happen that, during the computation of a function, some curve has value up until a certain point and
#     after it no values are present. (for example because the input wasn't long enough).
#     If this is the case this changer will fill this non-existing values with the last value the function has.
#
#     For example assume the curves:
#
#         - A: `<0,1> <3,4> <10,5>`
#         - B: `<0,6>`
#
#     This curve changer will transform B into:
#
#         - A: `<0,1> <3,4> <10,5>`
#         - B: `<0,6> <3,6> <10,6>`
#
#     """
#
#     class Data:
#         def __init__(self):
#             self.final_x = None
#             self.final_y = None
#
#     def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Data:
#         return RepeatEndToFillCurve.Data()
#
#     def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Data) -> Data:
#         if value.final_x is None:
#             raise ValueError(f"""
#                 It seems that the curve start with a missing x! This is impossible because a curve
#                 should have at least one value. Otherwise it is basically empty!
#                 Name: {function_name}
#                 Curve: {curves.get_function(function_name)}""")
#         if value.final_y is None:
#             value.final_y = curves.get_function_y(function_name, value.final_x)
#         curves.update_function_point(function_name, x, value.final_y)
#         return value
#
#     def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
#         if value.final_y is None:
#             value.final_x = x
#         else:
#             raise ValueError(f"identified a x value '{x}' corresponding with a y '{curves.get_function_y(function_name, x)}' next to a value x '{value.final_x}' without y value")
#         return value
#
#
# class CurvesRelativeTo(ICurvesChanger):
#     """
#     the changer first sets a plot which is the "baseline" for all other plots.
#
#     then it compute the difference between another plot and the "baseline".
#     Finally it removes the "baseline" from the plot altogether.
#
#     If the baseline is not found, the changer goes into error
#     """
#
#     def __init__(self, baseline: str):
#         ICurvesChanger.__init__(self)
#         self.baseline = baseline
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#         if self.baseline not in curves:
#             raise KeyError(f"the baseline {self.baseline} not found in the curves generated!!!")
#
#         df = curves.to_dataframe()
#         for name in curves.function_names():
#             if name == self.baseline:
#                 continue
#             # we need to compute the difference
#             df.loc[:, name] = df.loc[:, name] - df.loc[:, self.baseline]
#
#         return DataFrameFunctionsDict.from_dataframe(df)
#
#
#
#
#
# class SortRelativeTo(ICurvesChanger):
#     """
#     The changer consider a baseline. It orders the baseline monotonically crescent and then reorder
#     the other plots according to the baseline order
#     """
#
#     def __init__(self, baseline: str, decrescent: bool = False):
#         ICurvesChanger.__init__(self)
#         self.baseline = baseline
#         self.decrescent = decrescent
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#
#         df = curves.to_dataframe()
#         df.sort_values(by=self.baseline, ascending=not self.decrescent, inplace=True)
#         return DataFrameFunctionsDict.from_dataframe(df)
#
#
# class ConditionCurveRemoval(ICurvesChanger):
#     """
#     A changer that removes curves if the given condition is not satisfied
#
#     Conditions maybe something like:
#
#     lambda
#
#     """
#
#     def __init__(self, condition: Callable[[str, "IFunctionsDict"], bool]):
#         """
#         initialize the removal
#
#         :param condition: a function of 2 parameters such that the first parameter is the function name while the
#         second is the actual function. Generates true if the function should be kept, false otherwise
#         """
#         self.condition = condition
#
#     def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
#
#         for name in curves.function_names():
#             if not self.condition(name, curves):
#                 curves.remove_function(name)
#
#         return curves




