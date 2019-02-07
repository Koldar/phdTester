import math
from typing import Any

from phdTester.model_interfaces import IAggregator


class SingleAggregator(IAggregator):
    """
    An aggregator that enforce the fule that you can set the y-value of an x-value once
    """

    def first_value(self, new: float = None) -> Any:
        return new

    def aggregate(self, old: Any, new: Any) -> Any:
        raise ValueError(f"the value {old} can be set only once! We cannot merge it with the new value {new}!")


class SumAggregator(IAggregator):

    def first_value(self, new: float = None) -> float:
        return new

    def aggregate(self, old: float, new: float) -> float:
        return old + new


class MeanAggregator(IAggregator):

    def __init__(self):
        self.n = 0
        self.mean = 0

    def first_value(self, new: float = None) -> float:
        self.n = 1
        self.mean = new
        return self.mean

    def aggregate(self, old: float, new: float) -> float:
        self.n += 1
        self.mean = self.mean + (new - self.mean)/self.n
        return self.mean


class SampleVarianceAggregator(IAggregator):
    """
    An aggregator keeping track of the sample variance


    https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_Online_algorithm
    """

    def __init__(self):
        self.n = 0
        self.mean_aggregator = MeanAggregator()
        self.mean = 0
        self.variance = 0

    def first_value(self, new: float = None) -> float:
        self.n = 1
        self.mean = self.mean_aggregator.first_value(new)
        self.variance = 0

        return self.variance

    def aggregate(self, old: float, new: float):
        old_mean = self.mean

        self.n += 1
        self.mean = self.mean_aggregator.aggregate(old_mean, new)
        self.variance = self.variance + ((new - old_mean) ** 2) / self.n - self.variance/(self.n-1)

        return self.variance


class SampleStandardDeviationAggregator(IAggregator):

    def __init__(self):
        self.variance_aggregator = SampleVarianceAggregator()
        self.variance = 0

    def first_value(self, new: float = None) -> float:
        self.variance = self.variance_aggregator.first_value(new)
        return math.sqrt(self.variance)

    def aggregate(self, old: float, new: float) -> float:
        old_variance = self.variance
        self.variance = self.variance_aggregator.aggregate(old_variance, new)

        return math.sqrt(self.variance)


class PopulationVarianceAggregator(IAggregator):

    def __init__(self):
        self.n = 0
        self.mean_aggregator = MeanAggregator()
        self.mean = 0
        self.variance = 0

    def first_value(self, new: float = None) -> float:
        self.n = 1
        self.mean = self.mean_aggregator.first_value(new)
        self.variance = 0

        return self.variance

    def aggregate(self, old: float, new: float):
        old_mean = self.mean

        self.n += 1
        self.mean = self.mean_aggregator.aggregate(old_mean, new)
        self.variance = self.variance + ((new - old_mean)*(new -self.mean) - self.variance)/self.n

        return self.variance


class PopulationStandardDeviationAggregator(IAggregator):

    def __init__(self):
        self.variance_aggregator = PopulationVarianceAggregator()
        self.variance = 0

    def first_value(self, new: float = None) -> float:
        self.variance = self.variance_aggregator.first_value(new)
        return math.sqrt(self.variance)

    def aggregate(self, old: float, new: float) -> float:
        old_variance = self.variance
        self.variance = self.variance_aggregator.aggregate(old_variance, new)

        return math.sqrt(self.variance)


class MaxAggregator(IAggregator):

    def __init__(self):
        pass

    def first_value(self, new: float = None) -> float:
        return new if new is not None else float("-inf")

    def aggregate(self, old: float, new: float) -> float:
        return old if old > new else new


class MinAggregator(IAggregator):

    def __init__(self):
        pass

    def first_value(self, new: float = None) -> float:
        return new if new is not None else float("+inf")

    def aggregate(self, old: float, new: float) -> float:
        return old if old < new else new
