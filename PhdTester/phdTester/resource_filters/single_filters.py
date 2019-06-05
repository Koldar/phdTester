from typing import Callable

from phdTester import KS001, IDataSource
from phdTester.common_types import KS001Str, DataTypeStr, PathStr
from phdTester.model_interfaces import ISingleCsvFilter

from io import StringIO

import pandas as pd


class KeyMappingCondition(ISingleCsvFilter):
    """
    Accepts a csv only if the condition is valid for the KS001 structure representing the datasource considered
    """

    def __init__(self, condition: Callable[[KS001], bool]):
        self.condition = condition

    def is_valid(self, path: PathStr, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: DataTypeStr, index: int) -> bool:
        return self.condition(csv_ks001)

    def reset(self):
        pass


class NeedsKeyMapping(ISingleCsvFilter):
    """
    Accepts csv only if the associated KS001 structure has a dictionary containing all the specified key mappings
    """

    def __init__(self, ks001: KS001):
        self._ks001 = ks001

    def reset(self):
        pass

    def is_valid(self, path: PathStr, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: DataTypeStr, index: int) -> bool:
        return self._ks001 in csv_ks001


class SizeBound(ISingleCsvFilter):

    def __init__(self, datasource: "IDataSource", min_required_size: int = None, max_required_size: int = None):
        self.min_required_size = min_required_size
        self.max_required_size = max_required_size
        self.datasource = datasource

    def reset(self):
        pass

    def is_valid(self, path: PathStr, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: DataTypeStr, index: int) -> bool:
        test_data = StringIO(self.datasource.get(path, csv_ks001str, data_type))
        rows = pd.read_csv(test_data).shape[0]
        if self.min_required_size is not None and rows < self.min_required_size:
            return False
        if self.max_required_size is not None and rows > self.max_required_size:
            return False
        return True
