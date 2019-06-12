from typing import Tuple, List

from phdTester import commons
from phdTester.common_types import KS001Str, PathStr, DataTypeStr, GetSuchInfo
from phdTester.model_interfaces import IComplexCsvFilter


class NumberBound(IComplexCsvFilter):
    """
    Accepts csvs up until a certain quota
    """

    def __init__(self, max_accepted: int):
        self.max_accepted = max_accepted
        self.csv_accepted = 0

    def reset(self):
        self.csv_accepted = 0

    def is_valid(self, path: PathStr, csv_ks0001str: KS001Str, csv_ks001: "KS001", data_type: DataTypeStr, index: int, csv_data: List[Tuple[str, "ITestContext", KS001Str, "KS001", str]]) -> bool:
        if self.csv_accepted < self.max_accepted:
            self.csv_accepted += 1
            return True
        return False
