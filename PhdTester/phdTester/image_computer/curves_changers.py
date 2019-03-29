import abc
import logging
import math
from typing import Dict, Callable, Union, Tuple, Any, Optional, Set, List

import numpy as np
import pandas as pd

from phdTester import commons
from phdTester.default_models import PandasFunction, Function2D, SeriesFunction
from phdTester.image_computer import aggregators
from phdTester.model_interfaces import ICurvesChanger, IFunction2D, IFunction2DWithLabel, ITestContext


class AbstractTransform(ICurvesChanger, abc.ABC):

    @abc.abstractmethod
    def _mapping(self, name: str, x: float, y: float) -> float:
        pass

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = {}

        for name, f in curves.items():
            new_f = SeriesFunction()
            for x, y in curves[name].xy_unordered_values():
                new_f[x] = self._mapping(name, x, curves[name][x])
            result[name] = new_f

        return result


class TransformX(ICurvesChanger):
    """
    Transform each xaxis of each curve passed to this changes
    """

    def __init__(self, mapping: Callable[[str, float, float], float]):
        AbstractTransform.__init__(self)
        self.mapping = mapping

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = {}
        for name, f in curves.items():
            new_f = SeriesFunction()
            for x, y in f.xy_unordered_values():
                new_f.update_point(self.mapping(name, x, y), y)
            result[name] = new_f

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

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        f = SeriesFunction()
        for x, y in curves[self.name].xy_unordered_values():
            f[x] = self._mapping(x, curves[self.name][x])

        del curves[self.name]
        name = self.new_name if self.new_name is not None else self.name
        curves[name] = f

        return curves


class SimpleTransform(AbstractSingleTransform):

    def __init__(self, name: str, mapping: Callable[[float, float], float], new_name: str = None):
        AbstractTransform.__init__(self, name, new_name=new_name)
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
    def _compute_f(self, x: float, curves: Dict[str, IFunction2D]) -> float:
        pass

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        new_f = SeriesFunction()
        for x in list(curves.values())[0].x_ordered_values():
            new_f[x] = self._compute_f(x, curves)

        curves[self.name] = new_f
        return curves


class SyntheticFunction(AbstractSyntheticFunction):
    """
    A curve changer which adds a new function in the array available. Used to generate derived functions
    """

    def __init__(self, name: str, f: Callable[[float, Dict[str, IFunction2D]], float]):
        AbstractSyntheticFunction.__init__(self, name)
        self.f = f

    def _compute_f(self, x: float, curves: Dict[str, IFunction2D]) -> float:
        return self.f(x, curves)


class SyntheticCount(AbstractSyntheticFunction):
    """
    Adds a synthetic function whose y associated to a x is the number of functions applied to x satisfying a particular criterion
    """

    def __init__(self, name: str, criterion: Callable[[str, float, float], bool]):
        AbstractSyntheticFunction.__init__(self, name)
        self.criterion = criterion

    def _compute_f(self, x: float, curves: Dict[str, IFunction2D]) -> float:
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

    def _compute_f(self, x: float, curves: Dict[str, IFunction2D]) -> float:
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

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result: Dict[str, IFunction2D] = {}

        functions_aggregators: Dict[str, Dict[float, "aggregators.IAggregator"]] = {}

        for name, f in curves.items():
            if name not in result:
                result[name] = SeriesFunction()
                functions_aggregators[name] = {}
            for x, y in f.xy_unordered_values():

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

                result[name][xslot] = functions_aggregators[name][xslot].aggregate(y)

        return result


class Print(ICurvesChanger):
    """
    A change which simply log the curves
    """

    def __init__(self, log_function: Callable[[str], Any]):
        ICurvesChanger.__init__(self)
        self.log_function = log_function

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        for name, f in curves.items():
            self.log_function(f"name = {name}")
            self.log_function(f"x [size={f.number_of_points()}] = {f.x_ordered_values()}")
            self.log_function(f"f = {str(f)}")

        return curves


class Identity(ICurvesChanger):
    """
    A changer that does nothing
    """

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
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

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:

        xaxis = set()
        for x, f in curves.items():
            xaxis = xaxis.union(f.x_unordered_values())

        for x, f in curves.items():
            for x in sorted(xaxis):
                if x not in f.x_unordered_values():
                    f[x] = self.value
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

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = {}

        to_remove = set()
        for name, f in curves.items():
            if self.min_size is not None and f.number_of_points() < self.min_size:
                to_remove.add(name)
            if self.max_size is not None and f.number_of_points() > self.max_size:
                to_remove.add(name)

        for name, f in curves.items():
            if name not in to_remove:
                result[name] = f

        return result


class TruncateToLowestX(ICurvesChanger):
    """
    When plot have different x axis shared axis, you may need to truncate the longest one.

    For example if 2 functions are

    A = 1;03 2;06 3;14
    B = 1;09 2;12 3;15 4;20; 5;30

    You may want to truncate be to have the same values of A
    """

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        # we get the minimum length of the curve
        min_length = min(map(lambda x: x.number_of_points(), curves.values()))

        # ok, truncate everything which is over min_length
        for name, f in curves.items():
            if f.number_of_points() > min_length:
                points_to_remove = set(map(lambda x: x[1], filter(lambda x: x[0] >= min_length, enumerate(f.x_ordered_values()))))
                for p in points_to_remove:
                    f.remove_point(p)

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
    def add_function(self, name: str, f: "IFunction2D"):
        pass

    @abc.abstractmethod
    def to_functions(self) -> Dict[str, "IFunction2D"]:
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
    def _get_group_name(self, i: int, name: str, function1: IFunction2D) -> str:
        """
        Given a function we're considering, generate the name of the group which the function will belong to

        Function sharing the same group name will belong to the group

        :param i: i-th function we've encountered
        :param name: name of the funciton `function1`
        :param function1: function considered
        :return: name fo the group to attahc the function to
        """
        pass

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        groups: Dict[str, "AbstractFunctionGroup"] = {}
        for i, (name, f) in enumerate(curves.items()):
            group_name = self._get_group_name(i, name, f)
            if group_name not in groups:
                groups[group_name] = self._get_new_group_instance(group_name)
            groups[group_name].add_function(name, f)

        # now we convert the groups into a Dict[str, IFunction2D]
        result = {}
        for name, group in groups.items():
            for new_name, new_function in group.to_functions().items():
                if new_name in result:
                    raise ValueError(f"function {new_name} cannot be added because is already present in the dictionary!")
                result[new_name] = new_function
        return result


class StatisticalGroup(AbstractFunctionGroup):
    """
    The function
    """

    def __init__(self, name: str, track_min: bool, track_max: bool, track_mean: bool, percentile_watched: int, ignore_infinities: bool):
        AbstractFunctionGroup.__init__(self, name)
        self.percentile_watched = percentile_watched

        self.max_f: "IFunction2D" = None
        self.max_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.min_f: "IFunction2D" = None
        self.min_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.median_f: "IFunction2D" = None
        self.median_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.lower_percentile_f: "IFunction2D" = None
        self.lower_percentile_f_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.upper_percentile_f: "IFunction2D" = None
        self.upper_percentile_f_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.mean_f: "IFunction2D" = None
        self.mean_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.n_f: "IFunction2D" = None
        self.n_aggregators: Dict[float, "aggregators.IAggregator"] = None
        self.ignore_infinities = ignore_infinities

        #TODO add this
        self.track_n = True

        if track_max:
            self.max_f = SeriesFunction()
            self.max_aggregators: Dict[float, "aggregators.IAggregator"] = {}
        if track_min:
            self.min_f = SeriesFunction()
            self.min_aggregators: Dict[float, "aggregators.IAggregator"] = {}
        if percentile_watched is not None:
            if not (0 <= percentile_watched <= 50):
                raise ValueError(f"percentile to watche needs to be between 0 and 50!")
            self.lower_percentile_f = SeriesFunction()
            self.lower_percentile_f_aggregators: Dict[float, "aggregators.IAggregator"] = {}
            self.upper_percentile_f = SeriesFunction()
            self.upper_percentile_f_aggregators: Dict[float, "aggregators.IAggregator"] = {}
            self.median_f = SeriesFunction()
            self.median_aggregators: Dict[float, "aggregators.IAggregator"] = {}
        if track_mean:
            self.mean_f = SeriesFunction()
            self.mean_aggregators: Dict[float, "aggregators.IAggregator"] = {}
        if self.track_n:
            self.n_f = SeriesFunction()
            self.n_aggregators: Dict[float, "aggregators.IAggregator"] = {}

    def to_functions(self) -> Dict[str, "IFunction2D"]:
        result = dict()

        if self.max_f is not None:
            result[f"{self.get_name()}_max"] = self.max_f
        if self.min_f is not None:
            result[f"{self.get_name()}_min"] = self.min_f
        if self.mean_f is not None:
            result[f"{self.get_name()}_average"] = self.mean_f
        if self.percentile_watched is not None:
            result[f"{self.get_name()}_percentile={self.percentile_watched}"] = self.lower_percentile_f
            result[f"{self.get_name()}_percentile={100 - self.percentile_watched}"] = self.upper_percentile_f
            result[f"{self.get_name()}_percentile={50}"] = self.median_f
        if self.n_f is not None:
            result[f"{self.get_name()}_n"] = self.n_f

        return result

    def add_function(self, name: str, f: "IFunction2D"):
        logging.debug("*" * 20)
        logging.debug(f"adding new function {name}!")
        # we loop over the x,y of the function and we update the statistical index.
        # each statistical index of the same x if idempedent. Each startistical indices of every x are
        # independent from another x.
        for x in f.x_ordered_values():

            for i, (aggregator, statistical_function, generator) in enumerate(zip(
                [self.max_aggregators, self.min_aggregators, self.mean_aggregators, self.lower_percentile_f_aggregators, self.upper_percentile_f_aggregators, self.median_aggregators, self.n_aggregators],
                [self.max_f, self.min_f, self.mean_f, self.lower_percentile_f, self.upper_percentile_f, self.median_f, self.n_f],
                [lambda x: aggregators.MaxAggregator(), lambda x: aggregators.MinAggregator(), lambda x: aggregators.MeanAggregator(), lambda x: aggregators.PercentileAggregator(self.percentile_watched), lambda x: aggregators.PercentileAggregator(100 - self.percentile_watched), lambda x: aggregators.PercentileAggregator(50), lambda x: aggregators.Count()],
            )):
                if statistical_function is None:
                    # when the user doesn't want to track a statistical index, the function is None
                    continue

                if x in [float('+inf'), float('-inf')] and self.ignore_infinities:
                    # ignoring infinite value
                    continue

                if x not in aggregator:
                    aggregator[x] = generator(x)

                new_value = aggregator[x].aggregate(f[x])
                statistical_function[x] = new_value


class StatisticalGrouper(AbstractGrouper):
    """
    A grouper which groups functions according to `get_group_name_f`.

    Then we compute statistical indices for each `x` axis values for each group. In other words, each group is
    synthesized in some curve representing statistical metrics trends. For example we can generate how the maximum,
    minimum anbd average vary on the same  `x` axis values, for each group.
    """

    def __init__(self, get_group_name_f: Callable[[int, str, "IFunction2D"], str], track_min: bool = False, track_max: bool = False, track_mean: bool = True, percentile_watched: int = None, ignore_infinities: bool = False):
        """

        :param get_group_name_f: function defining the group name of a given function.
             - first parameter is the index fo the function;
             - second parameter is the function name
             - third paramete is the function itself
        :param track_min: true fi you want to generate the minimum trend of each function group as well
        :param track_max: true fi you want to generate the maximum trend of each function group as well
        :param track_mean: true fi you want to generate the average trend of each function group as well
        :param percentile_watched: true fi you want to generate a percentile trend of each function group as well
        :param ignore_infinities: true if you want to ignore "infinite" values during the computation of the curvesd
        """
        AbstractGrouper.__init__(self)
        self.get_group_name_f = get_group_name_f
        self.track_min = track_min
        self.track_max = track_max
        self.track_mean = track_mean
        self.percentile_watched = percentile_watched
        self.ignore_infinities = ignore_infinities

    def _get_new_group_instance(self, group_name: str) -> AbstractFunctionGroup:
        return StatisticalGroup(group_name,
            track_mean=self.track_mean,
            track_max=self.track_max,
            track_min=self.track_min,
            percentile_watched=self.percentile_watched,
            ignore_infinities=self.ignore_infinities,
        )

    def _get_group_name(self, i: int, name: str, function1: IFunction2D) -> str:
        # we assume name is a ks001 representation
        return self.get_group_name_f(i, name, function1)


class MergeCurvesWithSameStuffUnderTest(ICurvesChanger):

    def __init__(self, name_to_test_context: Callable[[str], "ITestContext"], y_aggregator: aggregators.IAggregator):
        ICurvesChanger.__init__(self)
        self.y_aggregator = y_aggregator
        self.name_to_test_context = name_to_test_context

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = dict()

        # for k, v in curves.items():
        #     logging.critical(f"name = {k}\nvalue = {str(v)}")

        xaxis = list(curves.values())[0].x_ordered_values()
        for x in xaxis:
            self.y_aggregator.reset()

            for name, f in curves.items():
                # we assume the name of the function is a KS001 structure from where we can generate a test context
                tc = self.name_to_test_context(name)
                label = tc.ut.get_label()
                if label not in result:
                    result[label] = SeriesFunction()


                previous_y = self.y_aggregator.aggregate(f[x])
                result[self.label].update_point(x, previous_y)

        return result


class MergeCurves(ICurvesChanger):

    def __init__(self, label: str, y_aggregator: aggregators.IAggregator, label_aggregator: aggregators.IAggregator = None):
        ICurvesChanger.__init__(self)
        self.y_aggregator = y_aggregator
        self.label_aggregator = label_aggregator or aggregators.IdentityAggregator()
        self.label = label

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = dict()
        result[self.label] = SeriesFunction()

        # for k, v in curves.items():
        #     logging.critical(f"name = {k}\nvalue = {str(v)}")

        for x in list(curves.values())[0].x_ordered_values():
            self.y_aggregator.reset()
            self.label_aggregator.reset()
            for k, f in curves.items():

                previous_y = self.y_aggregator.aggregate(f[x])
                previous_label = self.label_aggregator.aggregate(f.get_label(x))

                if should_use_labels:
                    result[self.label].update_triple(x, previous_y, previous_label)
                else:
                    result[self.label].update_point(x, previous_y)

        return result


class CheckSameAxis(ICurvesChanger):

    def __init__(self):
        ICurvesChanger.__init__(self)

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
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


class AggregateAllIthXPoints(ICurvesChanger):
    """
    The curve changer will set the i-th x values of all the curves involved to share the same value.

    For example asdsume there are 3 plots:
     - A `<1,3> <5,3> <10,3>`
     - B `<0,3> <4,3> <9,3>`
     - A `<2,3> <6,3> <11,3>`

    Each of them has different x values. Assume you want all of them to have the same axis. To do so,
    you need to merge `1,0,2` into one value, `5,4,6` into another single value nad `10,9,11` into another
    single value.

    This curve changer do that. For exmaple, you can use a MeanAggregator to syntetize the average of the numbers.

    This curve changer is really useful when you need to make sure all the plot have the same x axis
    """

    def __init__(self, aggregator: aggregators.IAggregator):
        ICurvesChanger.__init__(self)
        self.aggregator = aggregator

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        # we get the maximum length of the curve
        max_length = max(map(lambda x: x.number_of_points(), curves.values()))

        # for k, v in curves.items():
        #     logging.critical(f"curves are {k} = {v}")

        # ok, now for every 1st value of the functions, we compute the average of the x first values
        # ok, now for every 2st value of the functions, we compute the average of the x second values
        # and so on...

        for x_index in range(max_length):
            # compute the aggregation from the points of the x_index-th x values of each curve
            self.aggregator.reset()
            new_value = None
            for name, f in curves.items():
                if f.number_of_points() > x_index:
                    new_value = self.aggregator.aggregate(f.get_ith_xvalue(x_index))

            # change the x values of each curve
            # curves which do not have the x_index-th value won't be altered
            # note that this procedure WON'T leave the x ordering the same!
            # for exmaple a funciton has the following x values: [1,2,3,10]. When we need to rearrange the "1",
            # aggregator tells us that it needs to be replaced with 2.3. But in this way the "first " value becomes
            # the second one. This may lead to problem if the aggregator decided that "2" needs to be transformed
            # into 2.1: the previous "second value" (2) is now the first in the curve!!!  (this because 2.3 > 2.1!)
            # To solve this
            for name, f in curves.items():
                if f.number_of_points() > x_index:
                    f.change_ith_x(x_index, new_value)

        return curves



class AbstractFillCurve(ICurvesChanger, abc.ABC):

    def _get_all_xs(self, curves: Dict[str, IFunction2D]) -> Set[float]:
        result = set()
        for name, f in curves.items():
            result.update(f.x_ordered_values())
        return result

    def _compute_max_length(self, curves: Dict[str, IFunction2D]) -> Tuple[str, int]:
        max_f = None
        max_length = None
        for x, f in curves.items():
            if max_f is None:
                max_f = x
            if max_length is None:
                max_length = f.number_of_points()
            if f.number_of_points() > max_length:
                max_f = x
                max_length = f.number_of_points()

        return max_f, max_length

    @abc.abstractmethod
    def _handle_x_not_in_function(self, x: float, function_name: str, f: IFunction2D, value: Any) -> Any:
        pass

    @abc.abstractmethod
    def _handle_x_in_function(self, x: float, function_name: str, f: IFunction2D, value: Any) -> Any:
        pass

    @abc.abstractmethod
    def _handle_begin_function_misses_values(self, name: str, f: IFunction2D) -> Any:
        pass

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        xaxis = sorted(list(self._get_all_xs(curves)))
        xaxis_len = len(xaxis)
        # max_f, max_length = self._compute_max_length(curves)

        # logging.debug(f"maximum is {max_length}")

        # logging.critical(f"xaxis of reference is (size= {len(list(curves[max_f].x_ordered_values()))}): {curves[max_f].x_ordered_values()}")
        for name, f in curves.items():
            if f.number_of_points() < xaxis_len:
                value = self._handle_begin_function_misses_values(name, f)
                for x in xaxis:
                    if x not in f.x_unordered_values():
                        value = self._handle_x_not_in_function(x, name, f, value)
                    else:
                        value = self._handle_x_in_function(x, name, f, value)

        return curves


class AbstractRepeatPreviousValueToFillCurve(AbstractFillCurve, abc.ABC):
    """
    If a function does not have a value on a specific x, we assigne to that x f[x-1    """

    def __init__(self,):
        AbstractFillCurve.__init__(self)

    @abc.abstractmethod
    def _handle_first_absent_value(self, x: float, function_name: str, f: IFunction2D) -> Optional[float]:
        pass

    def _handle_x_not_in_function(self, x: float, function_name: str, f: IFunction2D, value: Optional[float]) -> Optional[float]:
        if value is None:
            return self._handle_first_absent_value(x, function_name, f)
        else:
            f[x] = value
            return f[x]

    def _handle_x_in_function(self, x: float, function_name: str, f: IFunction2D, value: Optional[float]) -> float:
        return f[x]

    def _handle_begin_function_misses_values(self, name: str, f: IFunction2D) -> Optional[float]:
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

    def _handle_first_absent_value(self, x: float, function_name: str, f: IFunction2D) -> Optional[float]:
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

    def _handle_first_absent_value(self, x: float, function_name: str, f: IFunction2D) -> Optional[float]:
        f[x] = self.value
        return f[x]


class RepeatValueToFillCurve(AbstractFillCurve):

    def __init__(self, value: float):
        AbstractFillCurve.__init__(self)
        self.value = value

    def _handle_begin_function_misses_values(self, name: str, f: IFunction2D) -> Any:
        return (False, )

    def _handle_x_not_in_function(self, x: float, function_name: str, f: IFunction2D, value: Any) -> Any:
        f[x] = self.value
        return (True, )

    def _handle_x_in_function(self, x: float, function_name: str, f: IFunction2D, value: "Any") -> "Any":
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

    def _handle_begin_function_misses_values(self, name: str, f: IFunction2D) -> Data:
        return RepeatEndToFillCurve.Data()

    def _handle_x_not_in_function(self, x: float, function_name: str, f: IFunction2D, value: Data) -> Data:
        if value.final_x is None:
            raise ValueError(f"""
                It seems that the curve start with a missing x! This is impossible because a curve
                should have at least one value. Otherwise it is basically empty!
                Name: {function_name}
                Curve: {f}""")
        if value.final_y is None:
            value.final_y = f[value.final_x]
        f[x] = value.final_y
        return value

    def _handle_x_in_function(self, x: float, function_name: str, f: IFunction2D, value: Any) -> Any:
        if value.final_y is None:
            value.final_x = x
        else:
            raise ValueError(f"identified a x value '{x}' corresponding with a y '{f[x]}' next to a value x '{value.final_x}' without y value")
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

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        if self.baseline not in curves:
            raise KeyError(f"the baseline {self.baseline} not found in the curves generated!!!")
        result = {}
        for k, f in curves.items():
            if k == self.baseline:
                continue
            f = curves[k] - curves[self.baseline]
            result[k] = f
        return result


class SortAll(ICurvesChanger):
    """
    The changer picks all the curves and just sort each cof them monotonically independently

    This will of course destroy all the relation between them
    """

    def __init__(self, decrescent: bool = False):
        ICurvesChanger.__init__(self)
        self.decrescent = decrescent

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        # ok, first of all we convert all the functions into a single dataframe
        # iteration of tuple name, y values of function

        ys = {k: list(map(lambda xs: curves[k][xs], curves[k].x_ordered_values())) for k in curves}
        df = pd.DataFrame(ys)
        df = pd.DataFrame(np.sort(df.values, axis=0), index=df.index, columns=df.columns)

        d = commons.convert_pandas_data_frame_in_dict(df)
        result = {}
        for k, values in d.items():
            result[k] = Function2D()
            for x, v in zip(curves[k].x_ordered_values(), values):
                result[k].update_point(x, v)

        return result


class SortRelativeTo(ICurvesChanger):
    """
    The changer consider a baseline. It orders the baseline monotonically crescent and then reorder
    the other plots according to the baseline order
    """

    def __init__(self, baseline: str, decrescent: bool = False):
        ICurvesChanger.__init__(self)
        self.baseline = baseline
        self.decrescent = decrescent

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        # ok, first of all we convert all the functions into a single dataframe
        # iteration of tuple name, y values of function
        ys = {k: list(map(lambda xs: curves[k][xs], curves[k].x_ordered_values())) for k in curves}
        # ys['x'] = [x for x in curves[self.baseline].x_ordered_values()]

        df = pd.DataFrame(ys)
        # df.set_index('x', inplace=True)
        df = df.sort_values(self.baseline)
        # xaxis = list(df.index)

        # ok, now reconvert to curves
        d = commons.convert_pandas_data_frame_in_dict(df)
        result = {}

        # logging.critical(f"xaxis is {curves[self.baseline].x_ordered_values()}")
        # logging.critical(f"d is {list(d.items())}")

        for k, values in d.items():
            result[k] = Function2D()
            for x, v in zip(curves[self.baseline].x_ordered_values(), values):
                result[k].update_point(x, v)

        # for x in xaxis:
        #     for k, values in d.items():
        #         if k not in result:
        #             result[k] = Function2D()
        #         logging.critical(f"vlaues are {list(values)}")
        #         for v in values:
        #             result[k].update_point(x, v)

        # for name, f in result.items():
        #    logging.critical(f"{name} = {f}")
        # raise ValueError()
        return result


class Multiplexer(ICurvesChanger):
    """
    A changer that sequentially apply contained curves changers
    """

    def __init__(self, *changers: ICurvesChanger):
        self.changers = changers

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = curves

        for changer in self.changers:
            result = changer.alter_curves(result)

        return result


class ConditionCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves if the given condition is not satisfied

    Conditions maybe something like:

    lambda

    """

    def __init__(self, condition: Callable[[str, IFunction2D], bool]):
        """
        initialize the removal

        :param condition: a function of 2 parameters such that the first parameter is the function name while the
        second is the actual function. Generates true if the function should be kept, false otherwise
        """
        self.condition = condition

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = {}

        for name, f in map(lambda x: (x, curves[x]), curves):
            if self.condition(name, f):
                # ok, the plot is deemed ok
                result[name] = f

        return result


class LowCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves which maximum never go up a certain value
    """

    def __init__(self, threshold: float, threshold_included: bool = False):
        self.threshold = threshold
        self.threshold_included = threshold_included

    def alter_curves(self, curves: Dict[str, IFunction2D]) -> Dict[str, IFunction2D]:
        result = {}

        for name, f in map(lambda x: (x, curves[x]), curves):
            for y in f.y_unordered_value():
                if (y > self.threshold) or (self.threshold_included and y == self.threshold):
                    # ok, the plot is deemed ok
                    result[name] = f
                    break

        return result

