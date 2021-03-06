from typing import Dict

import phdTester as phd
import pandas as pd
from phdTester.common_types import PathStr, DataTypeStr
from phdTester.model_interfaces import IDataRowConverter
from phdTesterExample.models import PerformanceCsvRow


class SortPerformanceCsv(IDataRowConverter):

    def get_csv_row(self, d: Dict[str, str], path: "phd.PathStr", name: "phd.KS001Str", ks001: "phd.KS001",
                    data_type: "phd.DataTypeStr") -> "phd.ICsvRow":
        return PerformanceCsvRow()


class RunId(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField", test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, ks001: "phd.KS001", content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.run


class Time(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField", test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, ks001: "phd.KS001", content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.time


class SequenceSize(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField", test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, ks001: "phd.KS001", content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return test_context.te.sequenceSize


class CountTime(phd.IDataRowExtrapolator):

    def __init__(self, threshold: float):
        self.__threshold = threshold

    def fetch(self, factory: "SortResearchField", test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, ks001: "phd.KS001",
              content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.time < self.__threshold
