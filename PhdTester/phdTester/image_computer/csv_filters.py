from io import StringIO
from typing import Iterable, Callable, Tuple, List, Any, Dict

import pandas as pd

from phdTester.common_types import KS001Str
from phdTester.ks001.ks001 import KS001
from phdTester.model_interfaces import ICsvFilter, ITestContext, ISingleCsvFilter, IComplexCsvFilter, \
    INaiveCsvFilter, IDataSource, ITestContextCsvFilter


class DataTypeIs(INaiveCsvFilter):
    """
    The resources are accepted only if the data type field is one withihn a user specified set
    """

    def __init__(self, accepted_extensions: Iterable[str]):
        """

        :param accepted_extensions: the list of all the data type which this filter should accept
        """
        INaiveCsvFilter.__init__(self)
        self.extensions = accepted_extensions

    def is_valid(self, path: str, ks001: KS001Str, data_type: str, index: int) -> bool:
        return data_type in self.extensions

    def reset(self):
        pass


class PathContains(INaiveCsvFilter):
    """
    The csv accepted all contains in the path a user-specified string
    """

    def __init__(self, substring: str):
        """

        :param substring: the string every csv accepted by this filter contains
        """
        INaiveCsvFilter.__init__(self)
        self.substring = substring

    def is_valid(self, path: str, ks001: KS001Str, data_type: str, index: int) -> bool:
        return self.substring in path

    def reset(self):
        pass


class NameContains(INaiveCsvFilter):
    """
    The validness of a datasource depends if in its name a substring is found
    """

    def __init__(self, substring: str):
        INaiveCsvFilter.__init__(self)
        self.substring = substring

    def is_valid(self, path: str, ks001: KS001Str, data_type: str, index: int) -> bool:
        return self.substring in ks001

    def reset(self):
        pass


class KeyMappingCondition(ISingleCsvFilter):
    """
    Accepts a csv only if the condition is valid for the KS001 structure representing the datasource considered
    """

    def __init__(self, condition: Callable[[KS001], bool]):
        ISingleCsvFilter.__init__(self)
        self.condition = condition

    def is_valid(self, path: str, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int) -> bool:
        return self.condition(csv_ks001)

    def reset(self):
        pass


class NeedsKeyMapping(ISingleCsvFilter):
    """
    Accepts csv only if the associated KS001 structure has a dictionary containing all the specified key mappings
    """

    def __init__(self, ks001: KS001):
        ICsvFilter.__init__(self)
        self._ks001 = ks001

    def reset(self):
        pass

    def is_valid(self, path: str, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int) -> bool:
        return self._ks001 in csv_ks001


class NumberBound(IComplexCsvFilter):
    """
    Accepts csvs up until a certain quota
    """

    def __init__(self, max_accepted: int):
        ICsvFilter.__init__(self)
        self.max_accepted = max_accepted
        self.csv_accepted = 0

    def reset(self):
        self.csv_accepted = 0

    def is_valid(self, path: str, csv_ks0001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int,
                 csv_data: List[Tuple[str, "ITestContext", KS001Str, "KS001", str]]) -> bool:
        if self.csv_accepted < self.max_accepted:
            self.csv_accepted += 1
            return True
        return False


class SizeBound(ISingleCsvFilter):

    def __init__(self, datasource: "IDataSource", min_required_size: int = None, max_required_size: int = None):
        ICsvFilter.__init__(self)
        self.min_required_size = min_required_size
        self.max_required_size = max_required_size
        self.datasource = datasource

    def reset(self):
        pass

    def is_valid(self, path: str, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int) -> bool:
        test_data = StringIO(self.datasource.get_csv(path, csv_ks001str))
        rows = pd.read_csv(test_data).shape[0]
        if self.min_required_size is not None and rows < self.min_required_size:
            return False
        if self.max_required_size is not None and rows > self.max_required_size:
            return False
        return True


class ExcludeCsvWithExternalValues(ITestContextCsvFilter):
    """
    The csv filter filters away all the csv whose KS001 structure contains any values which is not present in a given
    list. Useful when you want to discard filters which are not compliant with the specification the user has given you

    """

    def __init__(self, stuff_under_test_allowed_values: Dict[str, List[Any]], test_environment_allowed_values: Dict[str, List[Any]]):
        super().__init__(self)
        self.stuff_under_test_allowed_values = stuff_under_test_allowed_values
        self.test_environment_allowed_values = test_environment_allowed_values

    def is_valid(self, path: str, csv_ks001str: KS001Str, data_type: str, csv_ks001: "KS001", tc: "ITestContext", index: int) -> bool:
        return tc.are_option_values_all_in(self.stuff_under_test_allowed_values, self.test_environment_allowed_values)

    def reset(self):
        pass

