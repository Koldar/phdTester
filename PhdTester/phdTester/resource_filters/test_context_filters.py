from typing import Dict

from phdTester import commons, KS001Str, DataTypeStr, ITestContext, KS001
from phdTester.common_types import SlottedClass
from phdTester.model_interfaces import ITestContextCsvFilter


class NumberPerStuffUnderTestBound(SlottedClass, ITestContextCsvFilter):
    """
    a filter that limits the csv which represents the same algorithm up until an upperbound

    If we fill such threshold for a particular algorithm, we start discarding away data
    """

    __slots__ = ('__max_accepted', '__csv_accepted')

    def __init__(self, max_accepted: int):
        self.__max_accepted = max_accepted
        self.__csv_accepted: Dict[str, int] = {}
        """
        keys are stuff under test name and values are the number of csvs we've encoutered with such ut
        """

    def is_valid(self, path: str, csv_ks001str: KS001Str, data_type: DataTypeStr, csv_ks001: "KS001",
                 tc: "ITestContext", index: int) -> bool:
        label = tc.ut.get_label()
        if self.__csv_accepted[label] > self.__max_accepted:
            return False
        elif label not in self.__csv_accepted:
            self.__csv_accepted[label] = 0
        else:
            self.__csv_accepted[label] += 1

    def reset(self):
        self.__csv_accepted.clear()
