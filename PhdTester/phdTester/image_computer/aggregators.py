import logging
import math
import multiprocessing
import os
import sys
from typing import Any, Iterable, List, Tuple

import numpy as np
import pandas as pd

from phdTester import commons
from phdTester.common_types import SlottedClass
from phdTester.functions import DataFrameFunctionsDict
from phdTester.model_interfaces import IAggregator, IFunctionsDict, ISlotValueFetcher

import dask.array as da
import dask.dataframe as dd


class Count(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).count()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class IdentityAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        raise NotImplementedError()


class SingleAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        raise ValueError(f"{self.__class__} cannot aggregate anything!")


class SumAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).sum()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class QuantizedSum(SlottedClass, IAggregator):
    """
    An aggregator which sum all the previously fetched elements but yields not the actual sum but
    a quantized version of it.

    So for example, assume you have the data stream 4, 5, 7,

    """

    __slots__ = ('__actual_sum', '__quantization_levels', '__slot_value_fetcher')

    def __init__(self, quantization_levels: List[float], slot_value_fetcher: "ISlotValueFetcher"):
        self.__actual_sum = 0
        self.__quantization_levels = quantization_levels
        self.__slot_value_fetcher = slot_value_fetcher

    def clone(self) -> "IAggregator":
        result = QuantizedSum(quantization_levels=self.__quantization_levels, slot_value_fetcher=self.__slot_value_fetcher)

        result.__actual_sum = self.__actual_sum

        return result

    def reset(self):
        self.__actual_sum = 0

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        raise NotImplementedError()

    def get_current(self) -> float:
        for lb, ub in commons.get_interval_ranges(self.__quantization_levels):
            if lb < self.__actual_sum <= ub:
                return self.__slot_value_fetcher.fetch(lb, ub, False, True)
        else:
            raise ValueError(f"""
                cannot retrieve the quantization level of sum {self.__actual_sum}! 
                Quantization levels allowed are {list(commons.get_interval_ranges(self.__quantization_levels))}""")

    def aggregate(self, new: float) -> float:
        self.__actual_sum += new
        return self.get_current()


class MeanAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).mean()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class SampleVarianceAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).var()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class SampleStandardDeviationAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).std()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class PopulationVarianceAggregator(SlottedClass, IAggregator):

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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).var()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class PopulationStandardDeviationAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).std()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class PercentileAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).quantile(self.__percentile/100)
        return DataFrameFunctionsDict.from_dataframe(tmp)


class MaxAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602
        tmp = pd.concat(map(lambda x: x.to_dataframe(), functions_dict), sort=False)
        tmp = tmp.groupby(tmp.index).max()
        return DataFrameFunctionsDict.from_dataframe(tmp)


class MinAggregator(SlottedClass, IAggregator):
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

    def with_pandas(self, functions_dict: "List[IFunctionsDict]") -> "IFunctionsDict":
        # see https://stackoverflow.com/a/19490199/1887602

        # fetch all function names
        function_names = set()
        xaxis = set()
        # TODO create a function for this
        for d in functions_dict:
            function_names = function_names.union(set(d.function_names()))
            xaxis = xaxis.union(set(d.to_dataframe().index))
        function_names = list(function_names)
        logging.debug(f"function names are (len={len(function_names)}) {function_names}")
        logging.info(f"xaxis is (len={len(xaxis)})")
        space_estimate = (len(xaxis) * len(function_names)* sys.getsizeof(np.float32(0)))/(1000*1000)
        logging.info(f"generating min data frame. This operation will require ABOUT {space_estimate} MB")

        # #TODO generlize the . Block code to handle MemoryError
        # dataframe = pd.DataFrame(np.nan, columns=function_names, dtype=np.float32, index=[]).to_sparse(fill_value=np.nan, kind='block')
        # dataframe = dataframe.reindex(xaxis)
        # logging.info(f"the dataframe requires {sys.getsizeof(dataframe)/1000} MB")
        # #dataframe.index = xaxis

        dataframe = pd.DataFrame(np.nan, columns=function_names, index=xaxis)
        logging.info(f"the dataframe requires {sys.getsizeof(dataframe)/1000} MB")
        dataframe.index = xaxis

        for i, function_name in enumerate(function_names):
            tmp = list(map(lambda x: dd.from_pandas(x.to_dataframe()[function_name], npartitions=os.cpu_count()), filter(lambda x: function_name in x.function_names(), functions_dict)))
            concat = dd.concat(tmp)
            series = concat.groupby(concat.index).min().compute(scheduler='threads')
            dataframe[function_name] = series
            logging.debug(f"done processing {i}-th function...")

        result = DataFrameFunctionsDict()
        result._dataframe = dataframe
        return result
