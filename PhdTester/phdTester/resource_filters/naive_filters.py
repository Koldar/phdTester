from typing import Iterable

from phdTester.common_types import KS001Str, DataTypeStr, PathStr
from phdTester.model_interfaces import INaiveCsvFilter


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

    def is_valid(self, path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> bool:
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

    def is_valid(self, path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> bool:
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

    def is_valid(self, path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> bool:
        return self.substring in ks001

    def reset(self):
        pass
