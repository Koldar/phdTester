import abc
import os

from phdTester import KS001
from phdTester.common_types import KS001Str

__doc__ = """
This module contains all the splitter we natively support.

Splitter allows you to generate csvs in a more advance way related to the vanilla way to generate them
"""

from typing import Tuple, Callable, Any

from phdTester.model_interfaces import IFunctionSplitter, ITestContext, ICsvRow


class BasedOnCsv(IFunctionSplitter):
    """
    Create a new function for each csv we're currently analyzing.

    The function name will be the name of the csv we're analyzing
    """

    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext",
                       csv_name: KS001Str, csv_ks001: KS001,
                       i: int, csv_outcome: "ICsvRow",
                       colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> Tuple[float, float, str]:

        return x, y, os.path.basename(csv_name)


class BaseOnCsvRow(IFunctionSplitter):
    """
    Create a new function for each csv row we're currently analyzing

    The function name will be the name of the csv we're analyzing, attached with the row number information
    """

    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext",
                       csv_name: KS001Str, csv_ks001: KS001,
                       i: int, csv_outcome: "ICsvRow",
                       colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> Tuple[float, float, str]:

        new_name = KS001.from_merging(csv_ks001, label="functionSplitter", csvRow=i)
        return x, y, new_name.dump_str(
            colon=colon,
            pipe=pipe,
            underscore=underscore,
            equal=equal,
        )


class GroupOnCSVContextSplitter(IFunctionSplitter, abc.ABC):

    def __init__(self, f: Callable[["ITestContext", str, int, "ICsvRow"], Any], new_name: Callable[[str, Any], str]):
        IFunctionSplitter.__init__(self)
        self.f = f
        self.new_name = new_name

    @abc.abstractmethod
    def get_group(self, value: Any, x: float, y: float, function_name: str, csv_tc: "ITestContext", csv_name: str, i: int, csv_output: "ICsvRow") -> Any:
        """
        generate the group the value `value` belongs to
        :param value: the value generated with function `f`
        :param x: the x point considered
        :param y: the y point considered
        :param function_name: the name of the function `x` and `y` tuple is supposed to go to
        :param csv_tc: the test context where this data has been generated from
        :param csv_name: the name of the data source containing `x` and `y`
        :param i: the index of the row we're handling
        :param csv_output: an object representing the row of the csv just read
        :return: a value representing the particular group where this `x` and `y` will go to
        """
        pass

    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext",
                       csv_name: str,
                       i: int, csv_outcome: "ICsvRow") -> Tuple[float, float, Any, str]:

        val = self.f(csv_tc, csv_name, i, csv_outcome)
        val = self.get_group(val, x, y, under_test_function_key, csv_tc, csv_name, i, csv_outcome)
        name = self.new_name(under_test_function_key, val)
        return x, y, name


class GroupOnCSVValue(GroupOnCSVContextSplitter):

    def __init__(self, group_size: float, f: Callable[["ITestContext", str, int, "ICsvRow"], Any], new_name: Callable[[str, Any], str]):
        GroupOnCSVContextSplitter.__init__(self, f, new_name)
        self.group_size = group_size

    def get_group(self, value: Any, x: float, y: float, function_name: str, csv_tc: "ITestContext", csv_name: str,
                  i: int, csv_output: "ICsvRow") -> Any:
        return int(float(value)/self.group_size)


# todo refactor
class GroupOnCSVContextValueSplitter(IFunctionSplitter):

    def __init__(self, f, new_name: Callable[[str, Any], str]):
        IFunctionSplitter.__init__(self)
        self.f = f
        self.new_name = new_name

    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext",
                       csv_name: str,
                       i: int, csv_outcome: "ICsvRow") -> Tuple[float, float, Any, str]:
        val = self.f(csv_tc, csv_name, i, csv_outcome)

        name = self.new_name(under_test_function_key, val)
        return x, y, name

# TODO should we remove it?
class GroupOnCSVSingleValueSplitter(IFunctionSplitter):
    """
    A Group on CSV splitter is a splitter which split the points generated in different plots all the same algorithm,
    but different contexts.

    For context I intend a value inside the CSV itself.
    Example you want to track the performance of a path planning algorithm depending on the difficulty of the query.
    There are 1000 of queries and you want to "group" those query depending on that. Assuming query "difficulty" is
    available in the data source, you can easily do so with this splitter.

    After using this splitter, we generate as many functions as there are distinct values in all the relevant csvs
    """

    def __init__(self, csv_column_name: str, csv_column_cast: Callable[[str], Any], new_name: Callable[[str, str, Any], str]):
        """
        Create a new instance of this splitter

        :param csv_column_name: the name of option in the csv row we need to group values on. This value should be
            one within :meth: `phdTester.model_interfaces.ICSVRow.options`
        :param csv_column_cast: a function used to cast the insteresting value from the CSV to the one you want (e.g.,
            "5" can be casted to int by setting this value to `int`)
        :param new_name: a lambda allowing you to fetch the function name of the function which will contain the x,y
            pair. Values are:
                - the function name that, before calling the splitter, was supposed to hold the x,y pair;
                - name of the option in the csv name relevant for you;
                - the value of the option, casted according `csv_column_cast`;
        """
        IFunctionSplitter.__init__(self)
        self.new_name = new_name
        self.csv_column_name = csv_column_name
        self.csv_column_cast = csv_column_cast

    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext",
                       csv_name: str,
                       i: int, csv_outcome: "ICsvRow") -> Tuple[float, float, Any, str]:
        option_value = csv_outcome.get_option(self.csv_column_name)
        option_value = self.csv_column_cast(option_value)
        name = self.new_name(under_test_function_key, self.csv_column_name, option_value)

        return x, y, name
