import abc
import logging
import math
from typing import Dict, Callable, Union, Tuple, Any, Optional, Set, List

import numpy as np
import pandas as pd

from phdTester import commons
from phdTester.functions import DataFrameFunctionsDict, SeriesFunction
from phdTester.image_computer import aggregators
from phdTester.model_interfaces import ICurvesChanger, IFunction2D, ITestContext, IFunctionsDict


class AbstractTransform(ICurvesChanger, abc.ABC):

    @abc.abstractmethod
    def _mapping(self, name: str, x: float, y: float) -> float:
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        for name in curves.function_names():
            for x, y in curves.get_ordered_xy(name):
                curves.update_function_point(name, x, self._mapping(name, x, curves.get_function_y(name, x)))
        return curves


class TransformX(ICurvesChanger):
    """
    Transform each xaxis of each curve passed to this changes
    """

    def __init__(self, mapping: Callable[[str, float, float], float]):
        AbstractTransform.__init__(self)
        self.mapping = mapping

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        result = DataFrameFunctionsDict.empty(functions=curves.function_names(), size=curves.max_function_length())

        for name in curves.function_names():
            for x, y in curves.get_ordered_xy(name):
                result.update_function_point(name, self.mapping(name, x, y), y)
        return result


class RemapInvalidValues(AbstractTransform):

    def __init__(self, value):
        AbstractTransform.__init__(self)
        self.value = value

    def _mapping(self, name: str, x: float, y: float) -> float:
        if y in [float('+inf'), float('-inf')]:
            return self.value
        elif math.isnan(y):
            return self.value
        else:
            return y


class StandardTransform(AbstractTransform):

    def __init__(self, mapping: Callable[[str, float, float], float]):
        AbstractTransform.__init__(self)
        self.mapping = mapping

    def _mapping(self, name: str, x: float, y: float) -> float:
        return self.mapping(name, x, y)


class AbstractSingleTransform(ICurvesChanger, abc.ABC):
    """
    A curve changer which map a function into another one. Basically it's a map over a single function
    """

    def __init__(self, name: str, new_name: str = None):
        ICurvesChanger.__init__(self)
        self.name = name
        self.new_name: Optional[str] = new_name

    @abc.abstractmethod
    def _mapping(self, x: float, y: float) -> float:
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        f = SeriesFunction()
        for x, y in curves[self.name].xy_unordered_values():
            f[x] = self._mapping(x, curves.get_function_y(self.name, x))

        del curves[self.name]
        name = self.new_name if self.new_name is not None else self.name
        curves.set_function(name, f)

        return curves


class SimpleTransform(AbstractSingleTransform):

    def __init__(self, name: str, mapping: Callable[[float, float], float], new_name: str = None):
        AbstractSingleTransform.__init__(self, name, new_name=new_name)
        self.mapping = mapping

    def _mapping(self, x: float, y: float) -> float:
        return self.mapping(x, y)


class AbstractSyntheticFunction(ICurvesChanger, abc.ABC):
    """
    A curve changer which adds a new function in the array available. Used to generate derived functions
    """

    def __init__(self, name: str):
        ICurvesChanger.__init__(self)
        self.name = name

    @abc.abstractmethod
    def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        for x in list(curves.values())[0].x_ordered_values():
            curves.update_function_point(self.name, x, self._compute_f(x, curves))
        return curves


class SyntheticFunction(AbstractSyntheticFunction):
    """
    A curve changer which adds a new function in the array available. Used to generate derived functions
    """

    def __init__(self, name: str, f: Callable[[float, "IFunctionsDict"], float]):
        AbstractSyntheticFunction.__init__(self, name)
        self.f = f

    def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
        return self.f(x, curves)


class SyntheticCount(AbstractSyntheticFunction):
    """
    Adds a synthetic function whose y associated to a x is the number of functions applied to x satisfying a particular criterion
    """

    def __init__(self, name: str, criterion: Callable[[str, float, float], bool]):
        AbstractSyntheticFunction.__init__(self, name)
        self.criterion = criterion

    def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
        result = 0
        for name, f in curves.items():
            if self.criterion(name, x, f[x]):
                result += 1
        return result


class SyntheticPercentage(SyntheticCount):
    """
    Adds a synthetic function whose y associated to a x is the percentage of functions applied to x satisfying a particular criterion.

    The percentage is expressed between [0,1]
    """

    def __init__(self, name: str, criterion: Callable[[str, float, float], bool]):
        SyntheticCount.__init__(self, name, criterion)

    def _compute_f(self, x: float, curves: "IFunctionsDict") -> float:
        result = 0
        for name, f in curves.items():
            if self.criterion(name, x, f[x]):
                result += 1
        return result/len(curves)


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

    If several points of the same curve goes into the same slot, they cwill be merged with an aggregator
    """

    def __init__(self, quantization_step: Union[List[float], Callable[[float], Tuple[float, float]]], aggregator: aggregators.IAggregator, slot_value: Callable[[float, float, float], float] = None):
        """
        Initialize the quantization

        :param quantization_step: represents the quantization step we need to apply. You can set it in 2 ways.
            First by listing the quantization level via a list (e.g., [1, 100, 500, 700]): so, if x=50, the quantization
            level will be (1,100). An error is thrown if no quantization level is found (e.g., x=1000). A more robust
            approach involve using a passing a lambda which has the following sigbnature:
             - input x: the x axis value to quantize;
             - output 1: the start value of the quantization level containing x;
             - output 2: the end value of the quantization level containing x;
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

        if isinstance(quantization_step, list):
            self.quantization_step = list(sorted(quantization_step))
        elif isinstance(quantization_step, Callable):
            self.quantization_step = quantization_step
        else:
            raise TypeError(f"quantization can either be a list or a callable. Invalid {type(quantization_step)}!")

        self.aggregator = aggregator
        self.slot_value = slot_value or self._default_slot_value

    def _default_slot_value(self, x: float, start_quant: float, end_quant: float) -> float:
        return end_quant

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        result: "IFunctionsDict" = DataFrameFunctionsDict.from_other(curves)

        functions_aggregators: Dict[str, Dict[float, "aggregators.IAggregator"]] = {}

        for name in curves.function_names():
            if name not in result:
                result[name] = SeriesFunction()
                functions_aggregators[name] = {}
            for x, y in curves.get_ordered_xy(name):

                if isinstance(self.quantization_step, list):
                    # the quantization is a list. Hence we fetch the 2 numbers representing the quantization step
                    for i, quantization_slot in enumerate(self.quantization_step):
                        if i == 0:
                            previous = 0
                        else:
                            previous = self.quantization_step[i-1]
                        if previous <= x < quantization_slot:
                            break
                    else:
                        raise ValueError(f" x value {x} does not vbelong to any quantization!")
                elif isinstance(self.quantization_step, Callable):
                    # quantization_step is a function. Calling it
                    previous, quantization_slot = self.quantization_step(x)
                else:
                    raise TypeError(f"quantization step can either be list or callable. Got {type(self.quantization_step)}!")

                xslot = self.slot_value(x, previous, quantization_slot)
                if xslot not in functions_aggregators[name]:
                    functions_aggregators[name][xslot] = self.aggregator.clone()

                result.update_function_point(name, xslot, functions_aggregators[name][xslot].aggregate(y))

        return result


class Print(ICurvesChanger):
    """
    A change which simply log the curves
    """

    def __init__(self, log_function: Callable[[str], Any]):
        ICurvesChanger.__init__(self)
        self.log_function = log_function

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        for name in curves.function_names():
            f = curves.get_function(name)
            self.log_function(f"name = {name}")
            self.log_function(f"x [size={f.number_of_points()}] = {curves.get_ordered_x_axis(name)}")
            self.log_function(f"f = {str(f)}")

        return curves


class Identity(ICurvesChanger):
    """
    A changer that does nothing
    """

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        return curves


class UseValueToFillCurve(ICurvesChanger):
    """
    Fill the values not existing of every function with a specified value

    It may happen that, during the computation of a function, some curve do not have some values (for example because
    the stuff under test required too much time and it was summarly killed). If this is the case this changer will
    fill this non-existing values with a default value
    """

    def __init__(self, value: Union[float, int]):
        ICurvesChanger.__init__(self)
        self.value = value

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        shared_xaxis = curves.get_union_of_all_xaxis()

        for name in curves.function_names():
            for x in shared_xaxis:
                if x not in curves.contains_function_point(name, x):
                    curves.update_function_point(name, x, self.value)
        return curves


class RemoveSmallCurve(ICurvesChanger):
    """
    The changer will remove from the plotting curves which do not have a compliant number of points
    """

    def __init__(self, min_size: int = None, max_size: int = None):
        """

        :param min_size: the minimum amount of points needed to avoid being removed.
            if the number of point is exactly `min_size` your curve **won't** be removed.
        :param max_size: the maximum amount of points needed to avoid being removed.
            if the number of point is exactly `min_size` your curve **won't** be removed.
        """
        ICurvesChanger.__init__(self)
        self.min_size = min_size
        self.max_size = max_size

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        for name in curves.function_names():
            if self.min_size is not None and curves.get_function(name).number_of_points() < self.min_size:
                curves.remove_function(name)
            if self.max_size is not None and curves.get_function(name).number_of_points() > self.max_size:
                curves.remove_function(name)

        return curves


class TruncateToLowestX(ICurvesChanger):
    """
    When plot have different x axis shared axis, you may need to truncate the longest one.

    For example if 2 functions are

    A = 1;03 2;06 3;14
    B = 1;09 2;12 3;15 4;20; 5;30

    You may want to truncate be to have the same values of A.

    In order to work the functions can't have missing values. For example the changer won't work on these functions

    A = 1;03 2;06 3;14
    B = 1;09 3;15 4;20; 5;30
    """

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        # we get the minimum length of the curve
        min_length = min(map(lambda x: x.number_of_points(), curves.functions()))

        # ok, truncate everything which is over min_length
        curves.drop_all_points_after(min_length)

        return curves


class AbstractFunctionGroup(abc.ABC):
    """
    A data structure representing the data inside a group of function.

    Data structure connected to :ref AbstractGrouper:
    """

    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

    @abc.abstractmethod
    def add_function(self, name: str, curves: "IFunctionsDict"):
        """
        operation to perform to add a function inside the current group

        :param name: name of the function to add
        :param curves: dictioary of functions where the function is located. It is garantueed that this
        dictionary contains a function of name `name`
        :return:
        """
        pass

    @abc.abstractmethod
    def to_functions(self) -> "IFunctionsDict":
        pass


class AbstractGrouper(ICurvesChanger, abc.ABC):
    """
    From several curves, it groups them in some way. Then it expand each group into one or more function.

    Sometimes when computing curver functions, you need to group different curves according to a specific criteria
    and then generate, for each group, some other functions. This abstract curve changer let's you do that

    """

    def __init__(self):
        ICurvesChanger.__init__(self)

    @abc.abstractmethod
    def _get_new_group_instance(self, group_name: str) -> "AbstractFunctionGroup":
        """
        Whenever we need to create a new group of functions, we call this function, initializing said new (empty) group

        :param group_name: the name of the group to create
        :return:  the new group initialized
        """
        pass

    @abc.abstractmethod
    def _get_group_name(self, i: int, name: str, curves: "IFunctionsDict") -> str:
        """
        Given a function we're considering, generate the name of the group which the function will belong to

        Function sharing the same group name will belong to the group

        :param i: i-th function we've encountered
        :param name: name of the funciton `function1`
        :param curves: the dictionaries of functions we used to retrieve the function
        :return: name fo the group to attahc the function to
        """
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        groups: Dict[str, "AbstractFunctionGroup"] = {}
        for i, (name, ) in enumerate(curves.function_names()):
            group_name = self._get_group_name(i, name, curves)
            if group_name not in groups:
                groups[group_name] = self._get_new_group_instance(group_name)
            groups[group_name].add_function(name, curves)

        # now we convert the groups into a "IFunctionsDict"
        result = DataFrameFunctionsDict()
        for name, group in groups.items():
            for new_name, new_function in group.to_functions().items():
                if new_name in result:
                    raise ValueError(f"function {new_name} cannot be added because is already present in the dictionary!")
                result.set_function(new_name, new_function)
        return result


class BoxPlotGroup(AbstractFunctionGroup):
    """
    A group that merges the functions within the same group and compute the statistical indices for boxplotting.

    The statistical indices for boxplotting are:
     - min
     - 50th-xth percentile
     - 50th+xth percentile
     - median
     - average

     The functions are merged together as follows:
     - if 2 functions have the same x value, the 2 y will concur to compute the statistical indices for the same "x"
     value
    """

    def __init__(self, name: str, percentile_watched: int, ignore_infinites: bool, generate_plots_ignoring_infinities: bool):
        AbstractFunctionGroup.__init__(self, name)
        self.percentile_watched = percentile_watched
        self.ignore_infinites = ignore_infinites
        self.generate_plots_ignoring_infinities = generate_plots_ignoring_infinities
        self.functions: "IFunctionsDict" = DataFrameFunctionsDict()

    def add_function(self, name: str, curves: "IFunctionsDict"):
        self.functions.set_function(name, curves.get_function(name))

    def _create_boxplot_functions(self, df: pd.DataFrame, suffix: str) -> "IFunctionsDict":
        result: "IFunctionsDict" = DataFrameFunctionsDict()

        result.set_function(
            f"{self.get_name()}_max{suffix}",
            SeriesFunction.from_dataframe(df.max(axis=1))
        )
        result.set_function(
            f"{self.get_name()}_min{suffix}",
            SeriesFunction.from_dataframe(df.min(axis=1))
        )
        result.set_function(
            f"{self.get_name()}_average{suffix}",
            SeriesFunction.from_dataframe(df.mean(axis=1))
        )
        result.set_function(
            f"{self.get_name()}_percentile={self.percentile_watched}{suffix}",
            SeriesFunction.from_dataframe(df.quantile(q=self.percentile_watched / 100., axis=1))
        )
        result.set_function(
            f"{self.get_name()}_percentile={100 - self.percentile_watched}{suffix}",
            SeriesFunction.from_dataframe(df.quantile(q=((100 - self.percentile_watched) / 100.), axis=1))
        )
        result.set_function(
            f"{self.get_name()}_percentile=50{suffix}",
            SeriesFunction.from_dataframe(df.median(axis=1))
        )
        result.set_function(
            f"{self.get_name()}_n {suffix}",
            SeriesFunction.from_dataframe(df.count(axis=1))
        )

        return result

    def to_functions(self) -> "IFunctionsDict":
        result: "IFunctionsDict" = DataFrameFunctionsDict()

        df = pd.DataFrame(result.to_dataframe())  # enforce a copy

        if self.generate_plots_ignoring_infinities:
            # we generate 2 set of boxplots, one considering infinities and the other not considering them
            with_infinities = self._create_boxplot_functions(df, "_withinfinities")
            without_infinities = self._create_boxplot_functions(df.replace(np.inf, np.NaN), '_withoutinfinities')
            result = with_infinities + without_infinities
        elif self.ignore_infinites:
            # by default dataframe operations ignore NaN. So we convert the infinities into Nan
            df.replace(np.inf, np.NaN, inplace=True)
            result = self._create_boxplot_functions(df, "_withoutinfinities")
        else:
            # ok we treat the data as is
            result = self._create_boxplot_functions(df, "")

        return result


class BoxPlotGrouper(AbstractGrouper):
    """
    A grouper which groups functions according to `get_group_name_f`.

    Then we compute statistical indices (relevant for box plot) for each `x` axis values for each group.
    In other words, each group is
    synthesized in some curve representing statistical metrics trends.
    """

    def __init__(self, get_group_name_f: Callable[[int, str, "IFunction2D"], str], percentile_watched: int,
                 ignore_infinities: bool = False, generate_plots_ignoring_infinities: bool = False):
        """

        :param get_group_name_f: function defining the group name of a given function.
             - first parameter is the index fo the function;
             - second parameter is the function name
             - third paramete is the function itself
        :param percentile_watched: the percentile to watch. If you want to look for the 25th and 75th quantile, write 25
        :param ignore_infinities: true if you want to ignore "infinite" values during the computation of the curves.
            Is overwritten by generate_plots_ignoring_infinities
        :param generate_plots_ignoring_infinities: if true, we will generate 2 sets of curves: the first set will
        contain min,max, quantiles considering infinites values. The second set will contain min, max, qwuantiles ignoring
        infinite values. Overrides ignore_infinites parameter.
        """
        AbstractGrouper.__init__(self)
        self.get_group_name_f = get_group_name_f
        self.percentile_watched = percentile_watched
        self.ignore_infinities = ignore_infinities
        self.generate_plots_ignoring_infinities = generate_plots_ignoring_infinities

    def _get_new_group_instance(self, group_name: str) -> AbstractFunctionGroup:
        return BoxPlotGroup(group_name,
                            percentile_watched=self.percentile_watched,
                            ignore_infinities=self.ignore_infinities,
                            generate_plots_ignoring_infinities=self.generate_plots_ignoring_infinities,
                            )

    def _get_group_name(self, i: int, name: str, function1: IFunction2D) -> str:
        # we assume name is a ks001 representation
        return self.get_group_name_f(i, name, function1)


class MergeCurvesWithSameStuffUnderTest(ICurvesChanger):

    def __init__(self, name_to_test_context: Callable[[str], "ITestContext"], y_aggregator: aggregators.IAggregator):
        ICurvesChanger.__init__(self)
        self.y_aggregator = y_aggregator
        self.name_to_test_context = name_to_test_context

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        result = DataFrameFunctionsDict()

        xaxis = list(curves.values())[0].x_ordered_values()
        for x in xaxis:
            self.y_aggregator.reset()

            for name in curves.function_names():
                # we assume the name of the function is a KS001 structure from where we can generate a test context
                tc = self.name_to_test_context(name)
                label = tc.ut.get_label()
                if label not in result:
                    result[label] = SeriesFunction()

                previous_y = self.y_aggregator.aggregate(curves.get_function_y(name, x))
                result.update_function_point(name, x, previous_y)

        return result


class MergeCurves(ICurvesChanger):

    def __init__(self, label: str, y_aggregator: aggregators.IAggregator):
        ICurvesChanger.__init__(self)
        self.y_aggregator = y_aggregator
        self.label = label

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        result = DataFrameFunctionsDict()

        for x in list(curves.values())[0].x_ordered_values():
            self.y_aggregator.reset()
            for name in curves.function_names():
                previous_y = self.y_aggregator.aggregate(curves.get_function_y(name, x))
                result.update_function_point(self.label, x, previous_y)
        return result


class CheckSameAxis(ICurvesChanger):

    def __init__(self):
        ICurvesChanger.__init__(self)

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        if not curves.functions_share_same_xaxis():
            xaxis = None
            xaxis_curve = None
            for name, f in curves.items():
                if xaxis is None:
                    xaxis = set(f.x_unordered_values())
                    xaxis_curve = name
                else:
                    other = set(f.x_unordered_values())
                    if xaxis != other:
                        raise ValueError(f"""X axis mismatch!
                            XAXIS BASELINE NAME = {xaxis_curve}
                            X AXIS CURVE MISMATCH NAME = {name}
                            BASELINE X AXIS LENGTH = {len(xaxis)}
                            CURVE X AXIS LENGTH = {len(other)}
                            BASELINE - CURVE = {sorted(xaxis.difference(other))}
                            CURVE - BASELINE = {sorted(other.difference(xaxis))}""")
        return curves


class AbstractFillCurve(ICurvesChanger, abc.ABC):

    def _compute_max_length(self, curves: "IFunctionsDict") -> Tuple[str, int]:
        return curves.get_function_name_with_most_points(), curves.max_function_length()

    @abc.abstractmethod
    def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
        pass

    @abc.abstractmethod
    def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
        pass

    @abc.abstractmethod
    def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Any:
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        xaxis = list((curves.get_union_of_all_xaxis()))
        xaxis_len = len(xaxis)
        # max_f, max_length = self._compute_max_length(curves)

        # logging.debug(f"maximum is {max_length}")

        # logging.critical(f"xaxis of reference is (size= {len(list(curves[max_f].x_ordered_values()))}): {curves[max_f].x_ordered_values()}")
        for name in curves.function_names():
            if curves.get_function_number_of_points(name) < xaxis_len:
                value = self._handle_begin_function_misses_values(name, curves)
                for x in xaxis:
                    if x not in curves.get_ordered_x_axis(name):
                        value = self._handle_x_not_in_function(x, name, curves, value)
                    else:
                        value = self._handle_x_in_function(x, name, curves, value)

        return curves


class AbstractRepeatPreviousValueToFillCurve(AbstractFillCurve, abc.ABC):
    """
    If a function does not have a value on a specific x, we assigne to that x f[x-1    """

    def __init__(self,):
        AbstractFillCurve.__init__(self)

    @abc.abstractmethod
    def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
        pass

    def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Optional[float]) -> Optional[float]:
        if value is None:
            return self._handle_first_absent_value(x, function_name, curves)
        else:
            curves.update_function_point(function_name, x, value)
            return curves.get_function_y(function_name, x)

    def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Optional[float]) -> float:
        return curves.get_function_y(function_name, x)

    def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Optional[float]:
        return None


class RepeatPreviousValueOrSetOneToFillCurve(AbstractRepeatPreviousValueToFillCurve):
    """
    If a function does not have a value on a specific x, we assigne to that x f[x-1].
    If the first value is the one which is absent, we simply assign it a given one.
    """

    def __init__(self):
        AbstractFillCurve.__init__(self, )
        self.first_x = set()
        """
        If the first values of the curves are absent, we keep track of them and as soon as we find an x sch it exists
        an y value we fill all the values to the just got value
        """

    def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
        self.first_x.add(x)
        return None


class RepeatPreviousValueOrFirstOneToFillCurve(AbstractRepeatPreviousValueToFillCurve):
    """
    If a function does not have a value on a specific x, we assigne to that x f[x-1].
    If the first value is the one which is absent, we simply wait until a value is detected. Then we populate all
    the missing values with the ewnly discovered one.
    """

    def __init__(self, value: float):
        AbstractFillCurve.__init__(self, )
        self.value = value

    def _handle_first_absent_value(self, x: float, function_name: str, curves: "IFunctionsDict") -> Optional[float]:
        curves.update_function_point(function_name, x, self.value)
        return curves.get_function_y(function_name, x)


class RepeatValueToFillCurve(AbstractFillCurve):

    def __init__(self, value: float):
        AbstractFillCurve.__init__(self)
        self.value = value

    def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Any:
        return (False, )

    def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
        curves.update_function_point(function_name, x, self.value)
        return (True, )

    def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: "Any") -> "Any":
        if value[0]:
            raise ValueError(f"detected a x {x} in function {function_name} which is not associated with a y value, but before it there was a x value associate to an y!")
        return (value[0], )


class RepeatEndToFillCurve(AbstractFillCurve):
    """
    Fill the values not existing of every function with the last detected value

    It may happen that, during the computation of a function, some curve has value up until a certain point and
    after it no values are present. (for example because the input wasn't long enough).
    If this is the case this changer will fill this non-existing values with the last value the function has.

    For example assume the curves:

        - A: `<0,1> <3,4> <10,5>`
        - B: `<0,6>`

    This curve changer will transform B into:

        - A: `<0,1> <3,4> <10,5>`
        - B: `<0,6> <3,6> <10,6>`

    """

    class Data:
        def __init__(self):
            self.final_x = None
            self.final_y = None

    def _handle_begin_function_misses_values(self, name: str, curves: "IFunctionsDict") -> Data:
        return RepeatEndToFillCurve.Data()

    def _handle_x_not_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Data) -> Data:
        if value.final_x is None:
            raise ValueError(f"""
                It seems that the curve start with a missing x! This is impossible because a curve
                should have at least one value. Otherwise it is basically empty!
                Name: {function_name}
                Curve: {curves.get_function(function_name)}""")
        if value.final_y is None:
            value.final_y = curves.get_function_y(function_name, value.final_x)
        curves.update_function_point(function_name, x, value.final_y)
        return value

    def _handle_x_in_function(self, x: float, function_name: str, curves: "IFunctionsDict", value: Any) -> Any:
        if value.final_y is None:
            value.final_x = x
        else:
            raise ValueError(f"identified a x value '{x}' corresponding with a y '{curves.get_function_y(function_name, x)}' next to a value x '{value.final_x}' without y value")
        return value


class CurvesRelativeTo(ICurvesChanger):
    """
    the changer first sets a plot which is the "baseline" for all other plots.

    then it compute the difference between another plot and the "baseline".
    Finally it removes the "baseline" from the plot altogether.

    If the baseline is not found, the changer goes into error
    """

    def __init__(self, baseline: str):
        ICurvesChanger.__init__(self)
        self.baseline = baseline

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        if self.baseline not in curves:
            raise KeyError(f"the baseline {self.baseline} not found in the curves generated!!!")

        df = curves.to_dataframe()
        for name in curves.function_names():
            if name == self.baseline:
                continue
            # we need to compute the difference
            df.loc[:, name] = df.loc[:, name] - df.loc[:, self.baseline]

        return DataFrameFunctionsDict.from_dataframe(df)


class SortAll(ICurvesChanger):
    """
    The changer picks all the curves and just sort each cof them monotonically independently

    This will of course destroy all the relation between them. This can be used to generate a cactus plot
    """

    def __init__(self, decrescent: bool = False):
        ICurvesChanger.__init__(self)
        self.decrescent = decrescent

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":

        df = curves.to_dataframe()
        df = df.apply(lambda x: x.sort_values().values)
        return DataFrameFunctionsDict.from_dataframe(df)


class SortRelativeTo(ICurvesChanger):
    """
    The changer consider a baseline. It orders the baseline monotonically crescent and then reorder
    the other plots according to the baseline order
    """

    def __init__(self, baseline: str, decrescent: bool = False):
        ICurvesChanger.__init__(self)
        self.baseline = baseline
        self.decrescent = decrescent

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":

        df = curves.to_dataframe()
        df.sort_values(by=self.baseline, ascending=not self.decrescent, inplace=True)
        return DataFrameFunctionsDict.from_dataframe(df)


class ConditionCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves if the given condition is not satisfied

    Conditions maybe something like:

    lambda

    """

    def __init__(self, condition: Callable[[str, "IFunctionsDict"], bool]):
        """
        initialize the removal

        :param condition: a function of 2 parameters such that the first parameter is the function name while the
        second is the actual function. Generates true if the function should be kept, false otherwise
        """
        self.condition = condition

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":

        for name in curves.function_names():
            if not self.condition(name, curves):
                curves.remove_function(name)

        return curves


class LowCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves which maximum never go up a certain value
    """

    def __init__(self, threshold: float, threshold_included: bool = False):
        self.threshold = threshold
        self.threshold_included = threshold_included

    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":

        for name in curves.function_names():
            m = curves.max_of_function(name)
            if not((m > self.threshold) or (m == self.threshold and self.threshold_included is True)):
                curves.remove_function(name)

        return curves

