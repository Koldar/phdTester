import math
from typing import Any

import numpy as np

from phdTester import commons
from phdTester.model_interfaces import IAggregator


class Count(commons.SlottedClass, IAggregator):
    """
    An aggregator which keeps track of the number of values you have called this object onto
    """

    __slots__ = ('value', )

    def __init__(self):
        IAggregator.__init__(self)
        self.value = 0

    def clone(self) -> "IAggregator":
        result = Count()

        result.value = self.value

        return result

    def reset(self):
        self.value = 0

    def get_current(self) -> float:
        return self.value

    def aggregate(self, new: float) -> float:
        self.value += 1
        return self.value


class IdentityAggregator(commons.SlottedClass, IAggregator):
    """
    A fake aggregator which actually does not aggregate anything. IOt just return the new value
    """

    __slots__ = ('__value', )

    def __init__(self):
        self.__value = 0

    def clone(self) -> "IAggregator":
        result = IdentityAggregator()
        result.__value = self.__value
        return result

    def reset(self):
        self.__value = 0

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: float) -> float:
        self.__value = new
        return new


class SingleAggregator(commons.SlottedClass, IAggregator):
    """
    An aggregator that enforce the fule that you can set the y-value of an x-value once
    """

    __slots__ = ('__value',)

    def __init__(self):
        self.__value = None

    def clone(self) -> "IAggregator":
        result = SingleAggregator()
        result.__value = self.__value
        return result

    def reset(self):
        self.__value = None

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: Any) -> Any:
        if self.__value is not None:
            raise ValueError(f"the value {self.__value} can be set only once! We cannot merge it with the new value {new}!")
        self.__value = new
        return self.__value


class SumAggregator(commons.SlottedClass, IAggregator):
    """
    An aggregator which keeps track of the sum of all the values in a series
    """

    __slots__ = ('__value',)

    def __init__(self):
        self.__value = 0

    def clone(self) -> "IAggregator":
        result = SumAggregator()
        result.__value = self.__value
        return result

    def reset(self):
        self.__value = 0

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: float) -> float:
        self.__value = self.__value + new
        return self.__value


class MeanAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('n', 'mean', )

    def __init__(self):
        self.n = 0
        self.mean = 0

    def clone(self) -> "IAggregator":
        result = MeanAggregator()

        result.n = self.n
        result.mean = self.mean

        return result

    def reset(self):
        self.n = 0
        self.mean = 0

    def get_current(self) -> float:
        return self.mean

    def aggregate(self, new: float) -> float:
        self.n += 1
        self.mean = self.mean + (new - self.mean)/self.n
        return self.mean


class SampleVarianceAggregator(commons.SlottedClass, IAggregator):
    """
    An aggregator keeping track of the sample variance


    https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_Online_algorithm
    """

    __slots__ = ('n', 'mean_aggregator', 'mean', 'variance')

    def __init__(self):
        self.n = 0
        self.mean_aggregator = MeanAggregator()
        self.mean = 0
        self.variance = 0

    def clone(self) -> "IAggregator":
        result = SampleVarianceAggregator()

        result.n = self.n
        result.mean_aggregator = self.mean_aggregator.clone()
        result.mean = self.mean
        result.variance = self.variance

        return result

    def reset(self):
        self.n = 0
        self.mean_aggregator.reset()
        self.mean = 0
        self.variance = 0

    def get_current(self) -> float:
        return self.variance

    def aggregate(self, new: float):
        old_mean = self.mean

        self.n += 1
        self.mean = self.mean_aggregator.aggregate(new)
        self.variance = self.variance + ((new - old_mean) ** 2) / self.n - self.variance/(self.n-1)

        return self.variance


class SampleStandardDeviationAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('variance_aggregator', 'variance', )

    def __init__(self):
        self.variance_aggregator = SampleVarianceAggregator()
        self.variance = 0

    def clone(self) -> "IAggregator":
        result = SampleStandardDeviationAggregator()

        result.variance_aggregator = self.variance_aggregator.clone()
        result.variance = self.variance

        return result

    def reset(self):
        self.variance_aggregator.reset()
        self.variance = 0

    def get_current(self) -> float:
        return math.sqrt(self.variance)

    def aggregate(self, new: float) -> float:
        self.variance = self.variance_aggregator.aggregate(new)

        return math.sqrt(self.variance)


class PopulationVarianceAggregator(commons.SlottedClass, IAggregator):

    __slots__ = ('n', 'mean_aggregator', 'mean', 'variance')

    def __init__(self):
        self.n = 0
        self.mean_aggregator = MeanAggregator()
        self.mean = 0
        self.variance = 0

    def clone(self) -> "IAggregator":
        result = PopulationVarianceAggregator()

        result.n = self.n
        result.mean_aggregator = self.mean_aggregator.clone()
        result.mean = self.mean
        result.variance = self.variance

        return result

    def reset(self):
        self.n = 0
        self.mean_aggregator.reset()
        self.mean = 0
        self.variance = 0

    def get_current(self) -> float:
        return self.variance

    def aggregate(self, new: float):
        old_mean = self.mean

        self.n += 1
        self.mean = self.mean_aggregator.aggregate(new)
        self.variance = self.variance + ((new - old_mean)*(new - self.mean) - self.variance)/self.n

        return self.variance


class PopulationStandardDeviationAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('variance_aggregator', 'variance')

    def __init__(self):
        self.variance_aggregator = PopulationVarianceAggregator()
        self.variance = 0

    def clone(self) -> "IAggregator":
        result = PopulationStandardDeviationAggregator()

        result.variance_aggregator = self.variance_aggregator.clone()
        result.variance = self.variance

        return result

    def reset(self):
        self.variance_aggregator.reset()
        self.variance = 0

    def get_current(self) -> float:
        return math.sqrt(self.variance)

    def aggregate(self, new: float) -> float:
        self.variance = self.variance_aggregator.aggregate(new)

        return math.sqrt(self.variance)


class PercentileAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('__percentile', '__sequence', '__value')

    def __init__(self, percentile: int):
        IAggregator.__init__(self)
        self.__percentile = percentile
        self.__sequence = []
        self.__value = None

    def clone(self) -> "IAggregator":
        result = PercentileAggregator(percentile=self.__percentile)

        result.__sequence = self.__sequence[::]
        result.__value = self.__value
        return result

    def reset(self):
        self.__sequence = []
        self.__value = None

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: float) -> float:
        self.__sequence.append(new)
        self.__value = np.percentile(self.__sequence, self.__percentile)
        return self.__value


class MaxAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('__value',)

    def __init__(self):
        self.__value = float("-inf")

    def clone(self) -> "IAggregator":
        result = MaxAggregator()
        result.__value = self.__value
        return result

    def reset(self):
        self.__value = float("-inf")

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: float) -> float:
        self.__value = self.__value if self.__value > new else new
        return self.__value


class MinAggregator(commons.SlottedClass, IAggregator):
    __slots__ = ('__value',)

    def __init__(self):
        self.__value = float("+inf")

    def clone(self) -> "IAggregator":
        result = MinAggregator()
        result.__value = self.__value
        return result

    def reset(self):
        self.__value = float("+inf")

    def get_current(self) -> float:
        return self.__value

    def aggregate(self, new: float) -> float:
        self.__value = self.__value if self.__value < new else new
        return self.__value
