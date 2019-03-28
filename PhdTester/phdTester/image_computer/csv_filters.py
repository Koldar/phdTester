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


#TODO remove
# class IsOnTopOfGlobalIndex(IComplexCsvFilter):
#     """
#     A Csv filter that filters away CSV whose related KS001 have a field which is not within a certain set
#
#     The set is not statically specified, but it is retrieved by looking at another, more "global" CSV document
#     where this set can be computed one time.
#
#     In order to decide this set, we need to select a particular column in the "global document" and choose the csv
#     rows which have the highest value within that column. Then the set is chosen by looking at another column in the
#     csv.
#
#     Example
#     -------
#
#     Assume you have a csv called global.csv:
#
#     A B C
#     1 a 1
#     2 b 1
#     3 c 1
#     4 d 1
#     5 e 1
#     6 f 9
#     7 g 2
#
#     an you have several other csvs, one among is `|local:a=5,b=3|.csv`, whose content is irrelevant.
#     To check if `|local:a=5,b=3|.csv` belongs or not into the csvs which needs to be read in order to generate the
#     image, we run this structure with:
#
#      - `get_global_csv: lambda ks, tc: "global.csv"`
#      - `top_percentage`: 0.28
#      - `column_name`: "C"
#      - `relation_column_name`: "A"
#      - `get_ks_field`: lambda ks: ks["local"]["b"]
#
#     We first of all fetch with `get_ks_field` the field "b" (which is 3). Then we go to "global.csv" and we fetch the
#     row whose column "A" has the value of 3 (the row is `A=3, b=c, C=1`). Finally we check if the value "C" of said row
#     is within the greater 28% of the values in C. Since 28% or 7 rows is almost 1.96, we discard the csv since its value C
#     is not within the first 1.96 rows.
#
#
#     """
#
#     def reset(self):
#         self.set_detected = None
#
#     def __init__(self, top_percentage: float, relation_column_name: str, column_name: str, get_ks_field: Callable[["KS001"], int], get_global_csv: Callable[[str, "KS001", "ITestContext"], str]):
#         ICsvFilter.__init__(self)
#         self.top_percentage = top_percentage
#         self.column_name = column_name
#         self.relation_column_name = relation_column_name
#         self.set_detected = None
#         self.get_ks_field = get_ks_field
#         self.get_global_csv = get_global_csv
#
#     def is_valid(self, path: str, csv_ks0001str: KS001Str, csv_ks001: "KS001", tcm: "ITestContextMask", index: int,
#                      csv_abs_files: Iterable[str], csv_tcs: Iterable["ITestContext"]) -> bool:
#         if self.set_detected is None:
#             global_csv = self.get_global_csv(csv_abs_file, csv_ks001, csv_tcs[index])
#             df = pd.read_csv(global_csv)
#             rows = int(self.top_percentage * df.shape[0])
#             logging.critical(f"rows are {rows}")
#             # fetch rows whose column "columns" is among the top
#             largest_columns = df.nlargest(
#                 n=rows,
#                 columns=self.column_name
#             )
#             # fetch the value on "relation_column_name
#             self.set_detected = set(largest_columns[self.relation_column_name])
#             logging.critical(f"set detected to consider is {len(self.set_detected)}")
#
#         # now we need to check if the value from KS001 is among the one in set
#         value = self.get_ks_field(csv_ks)
#         return value in self.set_detected

