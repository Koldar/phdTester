import phdTester as phd
import pandas as pd
from phdTester.common_types import PathStr, DataTypeStr


class RunId(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField", test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.run


class Time(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField",test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.time


class SequenceSize(phd.IDataRowExtrapolator):
    def fetch(self, factory: "SortResearchField",test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str, content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return test_context.te.sequenceSize


class CountTime(phd.IDataRowExtrapolator):

    def __init__(self, threshold: float):
        self.__threshold = threshold

    def fetch(self, factory: "SortResearchField",test_context: "phd.ITestContext", path: PathStr, name: phd.KS001Str,
              content: pd.DataFrame,
              rowid: int, row: "phd.ICsvRow") -> float:
        return row.time < self.__threshold
