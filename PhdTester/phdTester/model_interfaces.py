import abc
import copy
import enum
import itertools
import logging

import numpy as np
import pandas as pd

from abc import ABC
from typing import Any, Tuple, Iterable, Dict, List, Callable, Optional, Set

from phdTester import constants
from phdTester.common_types import KS001Str, GetSuchInfo, PathStr, DataTypeStr
from phdTester.exceptions import ResourceTypeUnhandledError
from phdTester.graph import IMultiDirectedGraph
from phdTester.ks001.ks001 import KS001, Aliases


class OptionNodeKind(enum.Enum):
    FLAG = 0
    MULTIPLEXER = 1
    VALUE = 2
    SETTING = 3


class OptionBelonging(enum.Enum):
    SETTINGS = 0
    UNDER_TEST = 1
    ENVIRONMENT = 2


class ConditionKind(enum.Enum):
    IS_PRESENT = 0
    HAVE_VALUE = 1


class IOptionType(abc.ABC):
    """
    A interface representing the root element of every type which is accepted inside an option node in a option graph
    """
    pass


class IDependencyCondition(abc.ABC):

    @abc.abstractmethod
    def enable_sink_visit(self) -> bool:
        pass

    @abc.abstractmethod
    def is_required(self) -> bool:
        pass

    @abc.abstractmethod
    def accept(self, graph: IMultiDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        pass

    # @property
    # @abc.abstractmethod
    # def kind(self) -> ConditionKind:
    #     """
    #     Type of condition
    #     :return:
    #     """
    #     pass
    #
    # @abc.abstractmethod
    # def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
    #     """
    #     check if we should check the compliance of this condition
    #
    #     :param graph: the graph containing source_name and sink_name
    #     :param source_name: the source vertex of the condition
    #     :param sink_name: the sink vertex of the condition
    #     :param tc: the test context
    #     :return: true if we should check the accept method of this edge and follow this edge), false if the text
    #     context is not applicable to
    #     this edge
    #     """
    #     pass
    #
    # @abc.abstractmethod
    # def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
    #     """
    #     Check if this constraint is valid
    #
    #     :param graph: the graph containing the whole contraints
    #     :param source_name: name of the source node of this constraint
    #     :param sink_name: name of the sink node of this constraint
    #     :param tc: test context we're applying the constraint to
    #     :return: true if `tc` satisfies this constraint, false otherwise
    #     """
    #     pass


class IOptionNode(abc.ABC):
    """
    An node in the Option Graph representing a single option.

    """

    def __init__(self, kind: OptionNodeKind, long_name: str, option_type: type, ahelp: str, belonging: OptionBelonging):
        self.kind = kind
        self.long_name = long_name
        self.help = ahelp
        self.option_type = option_type
        self.belonging = belonging

    def get_parser_name(self) -> str:
        """
        For example "--verbose"

        return: the name of the option the CLI parser should assign to this node, plus the "--"
        """

        return "--{}".format(self.get_parser_attribute())

    def get_parser_attribute(self) -> str:
        """
        For example "verbose"

        return: the name of the option the CLI parser should assign to this node
        """
        return "{}{}".format(
            self.long_name.replace("-", "_"),
            "_values" if self.belonging != OptionBelonging.SETTINGS else ""
        )

    @abc.abstractmethod
    def add_to_cli_option(self, parser: Any):
        """
        Code to execute in order to add this option to a CLI parser software (i.e., argparse)
        :param parser: the parser where we need to add this option to
        :return:
        """
        pass

    @abc.abstractmethod
    def convert_value(self, value: Any) -> Any:
        """
        Method used to convert a value passed from the command line to a valid value compliant with the type of
        this option.
        For example if the CLi has --algorithms="['A*', 'WA*', 'HILL_CLIMBING']" this function will be called
        three times, each with the following `value` actual values:
         - A*
         - WA*
         - HILL_CLIMBING

        Depending on what the user has put on the command line, value can be:
         - a string;
         - a boolean;
         - a integer;
         - a float;


        :param value: a **single** value inside all the possible values of an option.
        :return: the actual value we're going to put into several ITestContext
        """
        pass


class ILabelable(abc.ABC):
    """
    something which can be labelled in some way
    """

    @abc.abstractmethod
    def get_label(self) -> str:
        """
        a human readable name of the element involved
        :return:
        """
        pass


class IOptionDict(abc.ABC):
    """
    Represents a class containing a mapping between a well-specified set of keys

    Keys are mandatory to be strings. Values can be anything you might and they **can** be se to None.
    The interface basically transforms an object into a querable dictionary thanks for methods like:

     - `set_opion`;
     - `get_option`;
     - `options`;

    You use this interface to allow you to let you implement all the methods without any fields.
    In this terminology, the keys are said **options**
    """

    @abc.abstractmethod
    def options(self) -> Iterable[str]:
        """

        :return: list of all the option names stored in the dictionary
        """
        pass

    @abc.abstractmethod
    def get_option(self, name: str) -> Any:
        """

        :param name: name of the option
        :return: fetch the value associated to the option name "name"
        :raise KeyError: if the option is not in the dictionary
        """
        pass

    @abc.abstractmethod
    def set_option(self, name: str, value: Any):
        """
        set the value of an options.

        It is considered error to set a key which is not inside the iterable generated by `options`.
        It is however allowed to set the same option more than once or set it even to None.

        :param name: the name of the option to set
        :param value: the value associated to such option
        :raise Exception: if the option does not exist in the object
        :return:
        """
        pass

    @abc.abstractmethod
    def __init__(self):
        """
        Generate a new instance of this structure, with uninitialized fields
        :return: a new instance of this structure
        """
        pass

    def contains_option(self, name: str) -> bool:
        """

        :param name: the option name to look for
        :return: true if the option called "name" is inside the dicitonary
        """
        return name in self.options()

    def to_dict(self, ignore_none: bool = True) -> Dict[str, Any]:
        """
        Generates a dictionary from this structure

        :param ignore_none: if True we will avoid addind to the dictionaries the keys whose values are None
        :return: a dictionary
        """

        result = {}
        for k in self.options():

            if (self.get_option(k) is not None) or (self.get_option(k) is None and not ignore_none):
                result[k] = self.get_option(k)

        return result

    def set_options(self, d: Dict[str, Any]):
        """
        Set multiple keys at once
        :param d: a dictionary containing the value to set
        :return:
        """
        for k in d:
            self.set_option(k, d[k])

    def clear(self):
        """
        Set everything in the dictionary as "None"

        :return:
        """
        for k in self.options():
            self.set_option(k, None)

    def keys(self) -> Iterable[str]:
        """
        Alias of `options`
        :return: iterable of all the options declared
        """
        return self.options()

    def clone(self, copy_function: Callable[[Any], Any] = None) -> "IOptionDict":
        """
        Creates a clone of this structure by copying the initialize values inside this very structure

        Values are copy by calling `copy.copy` if no `copy_function` is provided

        :param copy_function: if specified, we will use this function to copy the values
        :return:
        """
        copy_function = copy_function if copy_function is not None else copy.copy
        result = self.__class__()
        for o in self.options():
            result.set_option(o, copy_function(self.get_option(o)))
        return result

    def __contains__(self, option: str) -> bool:
        """
        Chekc if an option name is present in the object
        :param option: the option to check
        :return: true if the option is present in the object, false otherwise
        """
        return self.contains_option(option)

    def __getitem__(self, item: str) -> Any:
        """

        :param item: the option name to retrieve
        :return: the value associate to the options
        """
        return self.get_option(item)

    def __iter__(self) -> Iterable[Tuple[str, Any]]:
        """
        an iterable of pairs where the first value is the option while the second one is the related value
        :return:
        """
        for k in self.options():
            yield (k, self.get_option(k))

    def __eq__(self, other) -> bool:
        """
        Check if 2 IOptionDict are the same or not

        :param other: the other option dictionary to compare againts
        :return: true if the 2 dictionaries have the same keys and values storeed within themselves
        """
        if not isinstance(other, type(self)):
            return False
        for l in self.options():
            if self.get_option(l) != other.get_option(l):
                return False

        if len(list(self.options())) != len(list(other.options())):
            return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        """

        :return: dictionary representation (e.g., {a=5, b=hello})
        """
        return "{" + ", ".join(sorted(map(lambda k: f"{k}={self.get_option(k)}", self.options()))) + "}"

    def __str__(self):
        """

        :return: dictionary representation (e.g., {a=5, b=hello})
        """
        return "{" + ", ".join(sorted(map(lambda k: f"{k}={self.get_option(k)}", filter(lambda x: self.get_option(x) is not None, self.options())))) + "}"


class IOptionDictWithKS(IOptionDict, abc.ABC):
    """
    An Option dict which can also be converted with KS001 standard
    """

    @property
    @abc.abstractmethod
    def key_alias(self) -> Dict[str, str]:
        """
        Generate a dictionary where the  keys are the official key names while the valuesd are the aliases

        :return: structure needed to operate with KS001 alias system
        """
        pass

    @property
    @abc.abstractmethod
    def value_alias(self) -> Dict[str, str]:
        """
        Generate a dictionary where the keys are the official value names while the values are the aliases

        :return: structure needed to operate with KS001 alias system
        """
        pass

    def to_ks001(self, identifier: str = None, label: str = None) -> "KS001":
        """
        generate a KS001 structure containing the data within this dictionary

        the structure returned will have just one dictionary containing every options value within it

        :param identifier: the identifier of the new KS001. None if you want to generate a KS001 without any identifier
        :param label: the label of the dictionary to create. None if you want to generate a KS001 without any identifier
        :return:
        """

        return KS001.get_from(
            self.to_dict(),
            identifier=identifier,
            label=label,
            key_alias=self.key_alias,
            value_alias=self.value_alias
        )

    def set_from_ks001_index(self, index: int, ks: KS001):
        """
        Set the options of this dict directly from a KS001 instance

        inexistent key in this abstract dict won't be updated at all

        :param index: index of the dictionary which needs to be considered in the KS001 standard
        :param ks: the ks001 instance
        :return:
        """
        for o in ks[index]:
            if o in self.options():
                self.set_option(o, ks[index][o])

    def set_from_ks001_label(self, label: str, ks: KS001):
        """
        Set the options of this dict directly from a KS001 instance

        inexistent key in this abstract dict won't be updated at all

        :param label: name of the dictionary which needs to be considered in the KS001 standard
        :param ks: the ks001 instance
        :return:
        """
        for o in ks[label]:
            if o in self.options():
                self.set_option(o, ks[label][o])

    def populate_from_ks001_index(self, index: int, filename: str) -> "IOptionDictWithKS":
        """
        populate `this` fields with the key-value mapping in the i-th dictionary
        :param index: the index representing the dictiopnary where to fetch data from
        :param filename: the filename, absolute or relative, with or without extensiont containing the data to fetch
        :return:
        """
        ks = KS001.parse_filename(
            filename=filename,
            key_alias=Aliases(self.key_alias),
            value_alias=Aliases(self.value_alias),
            colon=constants.SEP_COLON,
            pipe=constants.SEP_PIPE,
            underscore=constants.SEP_PAIRS,
            equal=constants.SEP_KEYVALUE,
        )

        self.set_options(ks[index])
        return self

    def populate_from_ks001_name(self, label: str, filename: str) -> "IOptionDictWithKS":
        """
        populate `this` fields with the key-value mapping in the `label` named dictionary
        :param label: the label of the dictiopnary where to fetch data from
        :param filename: the filename, absolute or relative, with or without extension containing the data to fetch
        :return:
        """
        ks = KS001.parse_filename(
            filename=filename,
            key_alias=Aliases(self.key_alias),
            value_alias=Aliases(self.value_alias),
            colon=constants.SEP_COLON,
            pipe=constants.SEP_PIPE,
            underscore=constants.SEP_PAIRS,
            equal=constants.SEP_KEYVALUE,
        )

        self.set_options(ks[label])
        return self

    def clone(self, copy_function: Callable[[Any], Any] = None) -> "IOptionDictWithKS":
        return super(IOptionDictWithKS, self).clone(copy_function)


class ITestContext(IOptionDictWithKS, abc.ABC):
    """
    Something that represents a single performance test that we need to run

    A test context is, indirectly, also a KS001 because test contexts internal
    data can be used to generate values.
    """

    def __init__(self, ut: "IUnderTesting", te: "ITestingEnvironment"):
        IOptionDictWithKS.__init__(self)
        self._ut = ut
        self._te = te

    @property
    def ut(self) -> "IUnderTesting":
        """
        A view on all the options related to the stuff you want to test
        :return:
        """
        return self._ut

    @property
    def te(self) -> "ITestingEnvironment":
        """
        A view on all the options related to environment where you're testing your stuff
        :return:
        """
        return self._te

    def options(self) -> Iterable[str]:
        yield from self._ut.options()
        yield from self._te.options()

    def get_option(self, name: str) -> Any:
        if self._ut.contains_option(name):
            return self._ut.get_option(name)
        elif self._te.contains_option(name):
            return self._te.get_option(name)
        else:
            raise KeyError(f"option {name} not found!")

    def set_option(self, name: str, value: Any):
        if self._ut.contains_option(name):
            self._ut.set_option(name, value)
        elif self._te.contains_option(name):
            self._te.set_option(name, value)
        else:
            raise KeyError(f"option {name} not found!")

    def clone(self, copy_function: Callable[[Any], Any] = None) -> "ITestContext":
        ut = self._ut.clone(copy_function)
        te = self._te.clone(copy_function)
        return self.__class__(ut, te)

    def __eq__(self, other):
        if not isinstance(other, ITestContext):
            return False
        return self._ut == other._ut and self._te == other._te

    def __str__(self):
        return f"testing: {self._ut} environment: {self._te}"

    @property
    def key_alias(self) -> Dict[str, str]:
        result = {}
        result.update(self.ut.key_alias)
        result.update(self.te.key_alias)
        return result

    @property
    def value_alias(self) -> Dict[str, str]:
        result = {}
        result.update(self.ut.value_alias)
        result.update(self.te.value_alias)
        return result

    def are_option_values_all_in(self, stuff_under_test_dict_values: Dict[str, List[Any]], test_environment_dict_values: Dict[str, List[Any]]) -> bool:
        """
        Check if all the values inside this test context are inside the 2 given dictionaries

        Options with value None are automatically skipped

        :param stuff_under_test_dict_values: dictionary associating each option name of a stuff under test with all the possible values it can have
        :param test_environment_dict_values: dictionary associating each option name of a test environment with all the possible values it can have
        :return: true if every option value is inside those 2 dicitonaries (stuff under test values and test environment vlaues respectively), False otherwise
        """
        for o in self.ut.options():
            if self.ut.get_option(o) is None:
                continue
            if self.ut.get_option(o) not in stuff_under_test_dict_values[o]:
                return False

        for o in self.te.options():
            if self.te.get_option(o) is None:
                continue
            if self.te.get_option(o) not in test_environment_dict_values[o]:
                return False
        return True


class ICsvRow(IOptionDict, abc.ABC):
    """
    A class representing a single row fetched from the data source
    """

    def __init__(self):
        IOptionDict.__init__(self)


class IUnderTesting(IOptionDictWithKS, ILabelable, ABC):
    """
    An under testing reperesents the element you want to test within a ITestContext

    This structure may contains several options. The options values can be None.
    """

    def __init__(self):
        IOptionDictWithKS.__init__(self)
        ILabelable.__init__(self)

    def clone(self, copy_function: Callable[[Any], Any] = None) -> "IUnderTesting":
        return super(IUnderTesting, self).clone(copy_function=copy_function)


class ITestingEnvironment(IOptionDictWithKS, ILabelable, ABC):

    def __init__(self):
        IOptionDictWithKS.__init__(self)
        ILabelable.__init__(self)

    @abc.abstractmethod
    def get_order_key(self) -> str:
        """

        :return: a string generated for order several test environment
        """

    def clone(self, copy_function: Callable[[Any], Any] = None) -> "ITestingEnvironment":
        return super(ITestingEnvironment, self).clone(copy_function=copy_function)


class ITestingGlobalSettings(IOptionDict, abc.ABC):

    def __init__(self):
        IOptionDict.__init__(self)


class IMask(IOptionDict, abc.ABC):

    def __init__(self):
        IOptionDict.__init__(self)

    def __iter__(self) -> Iterable[Tuple[str, "ITestContextMaskOption"]]:
        return IOptionDict.__iter__(self)

    def __getitem__(self, key: str) -> "ITestContextMaskOption":
        return IOptionDict.__getitem__(self, key)

    def is_simple_compliant(self, tc: "ITestContext") -> bool:
        """
        Check if a text context is compliant with all the masks which can be solved only with the given TestContext.
        This check is usually really fast and it does not require an additional (possible bigger) set of
        TestContext

        :param tc: the text context to check
        :return: true if all the masks implementing ISimpleTestContextMaskOption are valid.
        """
        return self.__is_compliant(tc, [], [ISimpleTestContextMaskOption])

    def is_complex_compliant(self, tc: "ITestContext", tc_data: List["ITestContext"]) -> bool:
        """
        Check if a text context is compliant with all the masks which can be solved only with the given TestContext.
        This check is usually really fast and it does not require an additional (possible bigger) set of
        TestContext

        :param tc: the text context to check
        :param tc_data: a list of all the other text contexts compliant with all the previous test context masks
        :return: true if all the masks implementing ISimpleTestContextMaskOption are valid.
        """
        return self.__is_compliant(tc, tc_data, [IComplexTestContextMaskOption])

    def __is_compliant(self, tc: "ITestContext", tc_data: List["ITestContext"], allowed_types: Iterable[type]) -> bool:
        i = None
        for o in self.options():
            expected: ITestContextMaskOption = self.get_option(o)
            actual = tc.get_option(o)
            if expected is None:
                continue
            if isinstance(expected, ISimpleTestContextMaskOption):
                if ISimpleTestContextMaskOption not in allowed_types:
                    continue
                if not expected.is_compliant(actual):
                    return False
            elif isinstance(expected, IComplexTestContextMaskOption):
                if IComplexTestContextMaskOption not in allowed_types:
                    continue
                if i is None:
                    i = tc_data.index(tc)
                if not expected.is_compliant(i, actual, tc_data):
                    return False
            else:
                raise TypeError(f"invalid type {type(expected)}! Only ISimpleTestContextMaskOption or IComplexTestContextMaskOption allowed!")
        return True

    def is_complaint_with_test_context(self, tc: "ITestContext", tcs: List["ITestContext"]) -> bool:
        """
        Check if a test context is compliant against the given mask

        :param tc: the test context we need to check
        :param tcs: a list of test context which are interepreted as the "test context pool". Some masks in order
            to correctly operates needs to check the value of an option of a test context not singularly, but related
            to a list of other test contexts. It is required that `tc` belongs to `tcs`
        :return: True if `tc` is compliant with the given mask, `False` otherwise
        """
        return self.__is_compliant(tc, tcs, [ISimpleTestContextMaskOption, IComplexTestContextMaskOption])

    def get_have_value_string(self, ignore_some_tcm_keys: Iterable[str], string_between_key_value: str = "=", string_between_pairs: str = " ") -> str:
        """
        Generate a string representing all the fixed values this mask requires a test context to have

        The string representation will ignore all the other masks which can't generate a well specified
        value.

        :param ignore_some_tcm_keys: a keys in the IMaks that we explicitly want to ignore
        :param string_between_key_value: the string to put between an option name and option value
        :param string_between_pairs: the string to put between 2 different options mapping
        :return: something like "density=5% range=[3,4]"
        """
        result = []
        if ignore_some_tcm_keys is None:
            ignore_some_tcm_keys = []
        for o in filter(lambda x: x not in ignore_some_tcm_keys, self.options()):
            mask: "ITestContextMaskOption" = self.get_option(o)
            if mask.represents_a_well_specified_value():
                if mask.get_well_specified_value() is not None:
                    result.append(f"{o}{string_between_key_value}{mask.get_well_specified_value_as_string()}")
        return string_between_pairs.join(result)


class IStuffUnderTestMask(IMask, abc.ABC):

    def __init__(self):
        IMask.__init__(self)


class ITestEnvironmentMask(IMask, abc.ABC):

    def __init__(self):
        IMask.__init__(self)


class ITestContextMask(IMask, abc.ABC):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        IMask.__init__(self)
        self._ut = ut
        self._te = te

    @property
    def ut(self) -> "IStuffUnderTestMask":
        return self._ut

    @property
    def te(self) -> "ITestEnvironmentMask":
        return self._te

    def options(self) -> Iterable[str]:
        yield from self.ut.options()
        yield from self.te.options()

    def get_option(self, name: str) -> Any:
        if self.ut.contains_option(name):
            return self.ut.get_option(name)
        elif self.te.contains_option(name):
            return self.te.get_option(name)
        else:
            raise KeyError(f"{name} is not found in TestContextMask")

    def set_option(self, name: str, value: Any):
        if self.ut.contains_option(name):
            self.ut.set_option(name, value)
        elif self.te.contains_option(name):
            self.te.set_option(name, value)
        else:
            raise KeyError(f"{name} is not found in TestContextMask")

    def to_well_specified_ks001(self, identifier: str = None, label: str = None, key_alias: Dict[str, str] = None, value_alias: Dict[str, str] = None) -> "KS001":
        """
        Generates a KS001 containing only the values of all the masks which represents a single, well specified, value
        Other masks will be omitted in the generation. Aside from not well specified values,  masks which ensure that
        the only specified value is None will be discarded as well, since KS001 standard explicitly prohibits None
        values

        ::note
        The generated KS001 will have only one dictionary.

        :param identifier: the optional identifier of the KS001 to generate
        :param label: the optional label of the dictionary to generate
        :return:
        """
        result = KS001(identifier=identifier)
        if key_alias is not None:
            for k in key_alias:
                result.add_key_alias(k, key_alias[k])
        if value_alias is not None:
            for k in value_alias:
                result.add_key_alias(k, value_alias[k])
        for o in self.options():
            mask = self.get_option(o)
            if mask.represents_a_well_specified_value():
                if mask.get_well_specified_value() is None:
                    continue
                if label is not None:
                    result.add_key_value(place=label, key=o, value=mask.get_well_specified_value())
                else:
                    result.add_key_value(place=0, key=o, value=mask.get_well_specified_value())

        return result


class IDataWriter(abc.ABC):

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abc.abstractmethod
    def writeline(self, data: Iterable[Any]):
        pass


class IFunction2D(abc.ABC):

    @abc.abstractmethod
    def __init__(self):
        pass

    @abc.abstractmethod
    def update_point(self, x: float, y: float):
        pass

    @abc.abstractmethod
    def remove_point(self, x: float):
        pass

    @abc.abstractmethod
    def get_y(self, x: float) -> float:
        pass

    @abc.abstractmethod
    def number_of_points(self) -> int:
        pass

    @abc.abstractmethod
    def x_unordered_values(self) -> Iterable[float]:
        pass

    @abc.abstractmethod
    def y_unordered_value(self) -> Iterable[float]:
        pass

    @abc.abstractmethod
    def to_series(self) -> pd.Series:
        pass

    @abc.abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        pass

    @classmethod
    def from_xy(cls, x: Iterable[float], y: Iterable[float]) -> "IFunction2D":
        """
        Create a new function from 2 lists of the same length
        :param x: the x values
        :param y: the y values
        :return: a new function
        """
        result = cls()
        for x, y in zip(x, y):
            result.update_point(x, y)
        return result

    def has_ith_xvalue(self, i: int) -> bool:
        """
        Check if this function has a certain amount of values
        :param i:
        :return:
        """
        return self.number_of_points() > i

    def has_x_value(self, x: float) -> bool:
        return x in self.x_unordered_values()

    def get_ith_xvalue(self, i: int) -> float:
        """
        fetch the i-th x value of the function.

        If the function is: `<1,3> <5,3> <10,12>`
        callinf the function with `i=1` will return `5`

        :param i: the index fo the x_value to generate
        :return: an x value
        """

        return self.x_ordered_values()[i]

    def keys(self) -> Iterable[float]:
        """

        :return: alias of x_unordered_values
        """
        return self.x_unordered_values()

    def x_ordered_values(self) -> Iterable[float]:
        return sorted(self.x_unordered_values())

    def y_ordered_value(self) -> Iterable[float]:
        """

        :return: iterable of y values. Order is garantueed
        """
        return sorted(self.y_unordered_value())

    def xy_unordered_values(self) -> Iterable[Tuple[float, float]]:
        """

        :return: iterable of pair os x,y. Order is **not** garantueed
        """
        return map(lambda x: (x, self.get_y(x)), self.x_unordered_values())

    def xy_ordered_values(self) -> Iterable[Tuple[float, float]]:
        """

        :return: iterable of pairs of x,y. Order of x **is** garantueed. Order of y is ignored
        """
        return map(lambda x: (x, self.get_y(x)), self.x_ordered_values())

    def change_ith_x(self, x_index: int, new_value: float):
        x = self.get_ith_xvalue(x_index)
        y = self.get_y(x)
        self.remove_point(x)
        self.update_point(new_value, y)

    def change_x(self, old_x: float, new_x: float, overwrite: bool = False):
        if self.has_x_value(new_x) and overwrite is False:
            raise ValueError(f"cannot replace an already existing value!")
        if new_x == old_x:
            return
        old_y = self.get_y(old_x)
        self.update_point(new_x, old_y)
        self.remove_point(old_x)

    def __contains__(self, item: float) -> bool:
        """

        :param item: the x vcalue to check
        :return: true if a x value is present in the function, false otherwise
        """
        return self.has_x_value(item)

    def __setitem__(self, x: float, y: float):
        """
        adds apoint in the function
        :param x: the x value
        :param y: the y value
        :return:
        """
        self.update_point(x, y)

    def __getitem__(self, x: float) -> float:
        """

        :param x: the x value involved
        :return: the y whose x value is x
        """
        return self.get_y(x)

    def __add__(self, other: "IFunction2D") -> "IFunction2D":
        result = self.__class__()
        for x, y in self.xy_unordered_values():
            if x not in other:
                raise ValueError(f"the 2 functions has different x. Self has {x} while other don't!")
            result[x] = y + other[x]
        return result

    def __iadd__(self, other: "IFunction2D"):
        for x, y in self.xy_unordered_values():
            if x not in other:
                raise ValueError(f"the 2 functions has different x. Self has {x} while other don't!")
            self[x] = self[x] + other[x]

    def __sub__(self, other: "IFunction2D") -> "IFunction2D":
        result = self.__class__()
        for x, y in self.xy_unordered_values():
            if x not in other:
                raise ValueError(f"the 2 functions has different x. Self has {x} while other don't!")
            result[x] = y - other[x]
        return result

    def __isub__(self, other: "IFunction2D"):
        for x, y in self.xy_unordered_values():
            if x not in other:
                raise ValueError(f"the 2 functions has different x. Self has {x} while other don't!")
            self[x] = self[x] - other[x]

    def __str__(self) -> str:
        result = "{"
        result += ', '.join(map(lambda x: f"{x:.1f}={self[x]:.1f}", self.x_ordered_values()))
        result += "}"
        return result


class IFunctionsDict(abc.ABC):
    """
    A dictionary of functions
    """

    @abc.abstractmethod
    def function_names(self) -> Iterable[str]:
        """
        iterable of function names
        :return:
        """
        pass

    @abc.abstractmethod
    def functions(self) -> Iterable["IFunction2D"]:
        """
        iterable of functions
        :return:
        """
        pass

    @abc.abstractmethod
    def size(self) -> int:
        """
        number of functions inside this structure
        :return:
        """
        pass

    @abc.abstractmethod
    def max_function_length(self) -> int:
        """

        :return: the maximum number of points the function inside the dict has
        """
        pass

    @abc.abstractmethod
    def get_function(self, name: str) -> "IFunction2D":
        """

        :note: it is not garantueed that changes of the return value will be propagated to the content
        of this dictionary. In other words, it is not garantueed that the return value is generated by
        reference nor by value. It is recommended to use the return value only for constant operations.

        :param name: function name to retrieve
        :return: the fgunction whose namke is `name`
        :raise KeyError: if no function with the given name is found
        """
        pass

    @abc.abstractmethod
    def set_function(self, name: str, f: "IFunction2D"):
        pass

    @abc.abstractmethod
    def remove_function(self, name: str):
        """
        Remove a function inside the dictionary
        :param name: the name of the function to remove
        :raises KeyError: if the function is not present in the dictionary
        :return:
        """
        pass

    @abc.abstractmethod
    def contains_function(self, name: str) -> bool:
        """

        :param name: the function to check
        :return: true if the function is inside the dictionary
        """
        pass

    @abc.abstractmethod
    def contains_function_point(self, name: str, x: float) -> bool:
        """
        Check if a function has a particular x value
        :param name: the name fo the function to check
        :param x: the x value to check
        :return:  true if the function is defined on `x`, false otherwise
        """
        pass

    @abc.abstractmethod
    def get_function_y(self, name: str, x: float) -> float:
        """
        fetch hte y values of
        :param name: the name fo the function to check
        :param x: the value to check
        :raises KeyError: if the function is not defined on `x`
        :return:
        """
        pass

    @abc.abstractmethod
    def update_function_point(self, name: str, x: float, y: float):
        """
        Adds a new point or update an old one

        :param name: the function name
        :param x: the x value to update or create
        :param y: the y value to update or create
        :return:
        """
        pass

    @abc.abstractmethod
    def remove_function_point(self, name: str, x: float):
        """
        Removes a point from a function
        :param name: the function whose point we need to remove
        :param x: the point to remove
        :return:
        """
        pass

    @abc.abstractmethod
    def get_ordered_x_axis(self, name: str) -> Iterable[float]:
        """
        :param name: the function whose x axis we want to fetch
        :return: an ityerable of all the x where the function is defined. Order is garantueed
        """
        pass

    @abc.abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert the function dict into a dataframe

        the data frame needs to have as many columns as functions. The index should be the x values.
        Missing values of a given function should have NaN value.

        :return: the dataframe
        """
        pass

    @abc.abstractmethod
    def get_union_of_all_xaxis(self) -> Iterable[float]:
        """

        :return: an iterable of all the x values where at leasrt one function in the dictionary has been defined.
            Order is garantueed.
        """
        pass

    @abc.abstractmethod
    def get_function_number_of_points(self, name: str) -> int:
        """
        the number of points where the function is defined
        :param name: name of the function to work with
        :return:
        """
        pass

    @abc.abstractmethod
    def drop_all_points_after(self, x: float, x_included: bool = True):
        """
        Drop all the function points after a particular x value
        :param x: the x value involved
        :param x_included: true if we want to remove `x` as well, false otherwise
        :return:
        """
        pass

    @abc.abstractmethod
    def functions_share_same_xaxis(self) -> bool:
        """

        :return: true if all the functions share the same exact x axis, falsde otherwise
        """
        pass

    @abc.abstractmethod
    def get_ith_xvalue(self, name: str, x_index: int) -> float:
        """

        :param name: name of the function whose x axis value we want to fetch
        :param x_index: the i-th x axis value for the function
        :return: the x axis value requested
        """
        pass

    @abc.abstractmethod
    def change_ith_x(self, x_index: int, new_value: float):
        """
        Change the x value into a new value

        :param x_index: index of the x to alter
        :param new_value: new value to associate to the x
        :return:
        """
        pass

    @abc.abstractmethod
    def get_function_name_with_most_points(self) -> str:
        """

        :return: the name of the function which has the greatest number fo points defined
        """
        pass

    @abc.abstractmethod
    def max_of_function(self, name: str) -> float:
        """
        get maximum y value the function has
        :param name: the function to handle
        :return: max of f(x)
        """

    def get_ordered_xy(self, name: str) -> Iterable[Tuple[float, float]]:
        for x in self.get_ordered_x_axis(name):
            yield self.get_function_y(name, x)

    def keys(self) -> Iterable[str]:
        """
        iterable of function names
        :return:
        """
        yield from self.function_names()

    def values(self) -> Iterable["IFunction2D"]:
        yield from self.functions()

    def items(self) -> Iterable[Tuple[str, "IFunction2D"]]:
        for name in self.function_names():
            yield name, self.get_function(name)

    def __iter__(self) -> Iterable[str]:
        yield from self.function_names()

    def __getitem__(self, item: str) -> "IFunction2D":
        return self.get_function(item)

    def __setitem__(self, key: str, value: "IFunction2D"):
        self.set_function(key, value)

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, item: str) -> bool:
        return self.contains_function(item)

    def __delitem__(self, key: str):
        self.remove_function(key)



class AbstractDictionaryMergerTemplate(abc.ABC):

    @abc.abstractmethod
    def handle_key_missing_in_old(self, building_dict: Dict[float, float], new_k: float, new_value: float):
        pass

    @abc.abstractmethod
    def handle_key_missing_in_new(self, building_dict: Dict[float, float], removed_k: float, old_value: float):
        pass

    @abc.abstractmethod
    def handle_key_merging(self, building_dict: Dict[float, float], k: float, old_value: float, new_value: float):
        pass

    def merge_dictionaries(self, new_dict: Dict[float, float], old: Dict[float, float], new: Dict[float, float]) -> Dict[float, float]:
        old_set = set(old.keys())
        new_set = set(new.keys())

        for k in old_set.union(new_set):
            k_in_old = k in old
            k_in_new = k in new
            if not k_in_old and not k_in_new:
                raise ValueError(f"key {k} is not neither in old nor in new?!?!")
            elif k_in_old and not k_in_new:
                new_dict[k] = self.handle_key_missing_in_new(new_dict, k, old[k])
            elif not k_in_old and k_in_new:
                new_dict[k] = self.handle_key_missing_in_old(new_dict, k, new[k])
            elif k_in_old and k_in_new:
                self.handle_key_merging(new_dict, k, old[k], new[k])
            else:
                raise ValueError(f"where is {k}?")
        return new_dict


# TODO we should change the aggregator interface to have only a value called aggregate which accept a value.
# we should have other methods fetching the last value or check if a value has been inserted or not.
class IAggregator(abc.ABC):
    """
    Represents an object which merge different number in order to maintain a specific metric.

    For example, a mean aggregator keeps accepting a stream of number and maintains the average of
    the online succession
    """

    @abc.abstractmethod
    def clone(self) -> "IAggregator":
        """
        Create a new instance exactly the same as `self`
        :return: a new instance
        """
        pass

    @abc.abstractmethod
    def reset(self):
        """
        Reset the contents of this aggregator.

        :return:
        """

    @abc.abstractmethod
    def get_current(self) -> float:
        """

        :return: the value of the sequence at the moment
        """
        pass

    @abc.abstractmethod
    def aggregate(self, new: float) -> float:
        """
        Actions to perform when a new element of the sequence arrives

        For example assume you want to maintain the maximum of a sequence. Right now you have
        the maximum set to 6. Then you receive 3. 3 will be "new" and the function should return 6
        (the maximum of a sequence whose maximum is 6 and 3 is still 6).
        If you then received another value 9 the new maximum will be 9.

        :param new: the new value to accept
        :return: the value of the measurement you want to maintain after having received the new value
        """
        pass

    def aggregate_many(self, news: Iterable[float]) -> float:
        """
        Aggregate several values at once
        :param news: iterable of values to aggregate
        :return: value after all the input variables have been aggregated
        """
        tmp = None
        for n in news:
            tmp = self.aggregate(n)
        if tmp is None:
            raise ValueError(f"iterable is empty!")
        return tmp

    # @abc.abstractmethod
    # def aggregate(self, old: float, new: float) -> float:
    #     """
    #     Actions to perform when a new element of the sequence arrives
    #
    #     For example assume you want to maintain the maximum of a sequence. Right now you have
    #     the maximum set to 6. Then you receive 3. 6 will be "old", 3 will be "new" and the function should return 6
    #     (the maximum of a sequence whose maximum is 6 and 3 is still 6).
    #     If you then received another value 9 the new maximum will be 9.
    #
    #     :param old: the value of the measurement you want to maintain before the new value was detected
    #     :param new: the new value to accept
    #     :return: the value of the measurement you want to maintain after having received the new value
    #     """
    #     pass


class IFunctionSplitter(abc.ABC):
    """
    A function splitter allows to "split" a supposedly single plot into multiple plots. Useful if you're not satisfied
    with the granularity offered by Aggregator.

    Aggregator are useful, but maybe you're aggregating too much, thus losing information you might want to retain. Use
    a splitter to split the same function into different ones.
    """

    @abc.abstractmethod
    def fetch_function(self, x: float, y: float, under_test_function_key: str, csv_tc: "ITestContext", csv_name: str, i: int, csv_outcome: "ICsvRow") -> Tuple[float, float, str]:
        """
        alters the fetched point from the csvs

        :param x: the x point fetched from the csv
        :param y: the y point fetched from the csv
        :param under_test_function_key: the name of the function label to generate
        :param csv_tc: the test context used to fetch the csv
        :param csv_name: the absolute path of the csv name
        :param i: the index fo the row just read
        :param csv_outcome: a structure representing the single row of the csv just read
        :return: a tuple of 4 elements:
            - the new x vlaue,
            - the new y value
            - the new name of the function
        """
        pass


#TODO remove
class XAxisSharingEnum(enum.IntEnum):
    """
    Property of all the x axis inside a "IFunctionsDict" dictionary
    """
    SHARED = 0
    """
    The x axis among the functions is certain to be the same
    """
    DIFFERENT = 1


# TODO remove
class XAxisGeneratedEnum(enum.IntEnum):
    SHARED = 0
    DIFFERENT = 1
    """
    the x axis among the functions is certain to be different (although we don't know which functions have different
    xaxis)
    """
    UNALTERED = 2
    """
    During the procedure the functions xaxis have not been changed
    """
    UNKNOWN = 3
    """
    During the procedure the functions xaxis have been changed but we are unsure if the xaxis is shared, different
    or even unaltered
    
    This value is used when the output generated by a curve changer is unpredicable, thus more checks are needed
    """


class ICurvesChanger(abc.ABC):
    """
    Curve changers are objects which take in input the set of curves you need to plot inside a single graph
    and perform some operation on it.

    Curves changer are extremely useful when you want to tweak a a plot by doing something trivial.
    For example they can be used to add new generated curves, or remove peaks.
    """

    @abc.abstractmethod
    def alter_curves(self, curves: "IFunctionsDict") -> "IFunctionsDict":
        """
        perform the operation altering the curves

        :preconditions: We assume that x axis curves are compliant with

        :param curves: the curves to alter
        :return: a new set of functions to plot
        """
        pass

    # TODO remove
    # @abc.abstractmethod
    # def requires_functions_with_the_xaxis(self) -> Set[XAxisSharingEnum]:
    #     """
    #
    #     :return: the set of accepted x axis state `alter_curves` requires the x axis of `curves` to be
    #
    #     """
    #     pass
    #
    # @abc.abstractmethod
    # def xaxis_property_produced(self) -> XAxisExtendedEnum:
    #     """
    #
    #     :return: how all the x axis of the functions generated by `alter_curves` are
    #     """
    #     pass


#TODO this filters not only apply to csv, but theoretically to all the resources in the data source!
class ICsvFilter(abc.ABC):
    """
    A structure representing an object filtering data sources
    """

    @abc.abstractmethod
    def reset(self):
        pass

    @abc.abstractmethod
    def is_naive(self) -> bool:
        pass

    @abc.abstractmethod
    def is_single(self) -> bool:
        """
        mutually exclusive with is_complex

        :return: true if the filter is **independent** of other accepted data sources
        """
        pass

    @abc.abstractmethod
    def is_testcontext(self) -> bool:
        """
        mutually exclusive with the other is_XXX methods
        :return: true if trhe filter requires, to work, to access the "ITestContext" of the given resource
        """
        pass

    @abc.abstractmethod
    def is_complex(self) -> bool:
        """
        mutually exclusive with is_single

        :return: true f the filter is **dependent** with other accepted data sources
        """
        pass

    def as_naive(self) -> "INaiveCsvFilter":
        return self

    def as_single(self) -> "ISingleCsvFilter":
        return self

    def as_testcontext(self) -> "ITestContextCsvFilter":
        return self

    def as_complex(self) -> "IComplexCsvFilter":
        return self


class INaiveCsvFilter(ICsvFilter, abc.ABC):
    """
    a datasource filtering object whhose validity can be detected by looking only at the name of a single data source

    This filter is really simple and can be used to avoid more difficult computation. Howver, KS001 representation
    of the datasource name is not available. If you need it, use ISingleCsvFiltering
    """

    @abc.abstractmethod
    def is_valid(self, path: str, ks001: KS001Str, data_type: str, index: int) -> bool:
        """
        Check if a csv is valid based on its content

        :param path: the path where the csv resource is located
        :param ks001: name of the csv
        :param data_type: the type of the resource to filter
        :param index: the index of this csv
        :return: true if this csv needs to be considered when generating an image, false otherwise
        """
        pass

    def is_naive(self) -> bool:
        return True

    def is_single(self) -> bool:
        return False

    def is_testcontext(self) -> bool:
        return False

    def is_complex(self) -> bool:
        return False


class ISingleCsvFilter(ICsvFilter, abc.ABC):
    """
    A datasource filtering object whose validity can be detected by looking only at the single data source and its KS001
    """

    @abc.abstractmethod
    def is_valid(self, path: str, csv_ks001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int) -> bool:
        """
        Check if a csv is valid based on its content

        :param path: the path of the csv
        :param csv_ks001str: a string representation of csv_ks001
        :param csv_ks001: the KS001 representing the name of the csv
        :param data_type: the type of the resource to filter
        :param index: the index of this csv
        :return: true if this csv needs to be considered when generating an image, false otherwise
        """
        pass

    def is_naive(self) -> bool:
        return False

    def is_single(self) -> bool:
        return True

    def is_testcontext(self) -> bool:
        return False

    def is_complex(self) -> bool:
        return False


class ITestContextCsvFilter(ICsvFilter, abc.ABC):
    """
    Represents a resource filter which requires to have the relative "TestContext" in order to effectively work
    """

    @abc.abstractmethod
    def is_valid(self, path: str, csv_ks001str: KS001Str, data_type: str, csv_ks001: "KS001", tc: "ITestContext", index: int) -> bool:
        """
        Check if a csv is valid based on its content

        :param path: the path of the csv
        :param csv_ks001str: a string representation of csv_ks001
        :param data_type: the type of the resource to filter
        :param csv_ks001: the KS001 representing the name of the csv
        :param tc: the test context representing the csv filter
        :param index: the index of this csv
        :return: true if this csv needs to be considered when generating an image, false otherwise
        """
        pass

    def is_naive(self) -> bool:
        return False

    def is_single(self) -> bool:
        return False

    def is_testcontext(self) -> bool:
        return True

    def is_complex(self) -> bool:
        return False


class IComplexCsvFilter(ICsvFilter, abc.ABC):
    """
    A datasource filtering object whose validity can be checked only by looking a set of other datasources as well.
    """

    @abc.abstractmethod
    def is_valid(self, path: str, csv_ks0001str: KS001Str, csv_ks001: "KS001", data_type: str, index: int,
                 csv_data: List[GetSuchInfo]) -> bool:
        """
        Check if a csv is valid based on its content

        :param path: path of the csv in the datasource
        :param csv_ks0001str: string representation of the KS001 rerpesenting the CSV
        :param csv_ks001: the KS001 representing the csv
        :param data_type: the type of the resource to consider
        :param index: the index where `csv_ks001` can be found in `csv_data`
        :param csv_data: all the relevant csvs which have been filtered by the previous filters
        :return: true if this csv needs to be considered when generating an image, false otherwise
        """
        pass

    def is_naive(self) -> bool:
        return False

    def is_single(self) -> bool:
        return False

    def is_testcontext(self) -> bool:
        return False

    def is_complex(self) -> bool:
        return True


class ITestContextMaskOption(abc.ABC):
    """
    A value inside a ITestContextMask

    this value represents a condition that must be met by a concrete ITestContext option value
    to determine if the ITestContext is qualified for a certain operation.

    For example if we need all the test contexts with the option "foo" set to 5 we can code:

    test_context_mask.foo = needs_to_have_value(5)

    to say just that.
    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def represents_a_well_specified_value(self) -> bool:
        """
        Check if this mask deals with the fact that an option needs to have a well specified value.

        For example "ignore option value" should return False while "option needs to have a static value"
        should return True

        :return: True if this mask contains a well specified value
        """
        pass

    @abc.abstractmethod
    def get_well_specified_value(self) -> Any:
        """
        get the well-specified value

        Implies that represents_a_well_specified_value return true.
        This is mask dependent, hence for standard string representation is more safe to use
        get_well_specified_value_as_string
        :return:
        """

    @abc.abstractmethod
    def get_well_specified_value_as_string(self) -> str:
        """
        get the string representation of the well-specified value.

        Implies that represents_a_well_specified_value return true
        :return:
        """

    @abc.abstractmethod
    def set_params(self, **kwargs):
        """
        Set additional parameters that can be altered only in runtime

        Post condition:
         - After this operation, we can certainly know if a mask can operate or not

        :param kwargs: a dictionaries of options. They are mask dependent
        :return:
        """
        pass

    @property
    @abc.abstractmethod
    def can_operate(self) -> bool:
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass


class ISimpleTestContextMaskOption(ITestContextMaskOption):

    def __init__(self):
        ITestContextMaskOption.__init__(self)

    @abc.abstractmethod
    def is_compliant(self, actual: "Any") -> bool:
        pass


class IComplexTestContextMaskOption(ITestContextMaskOption):

    def __init__(self):
        ITestContextMaskOption.__init__(self)

    @abc.abstractmethod
    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        """
        Check if a option value is is compliant with this mask

        Masks can generally be of 2 types:
         - their compliance output depends entirely on the single option value
            (for example the "ignore" mask deals only with the specific test context where the option mask is evaluated);
         - their compliance output depends on the whole collection of test contexts involved. For example if an option
            "foo" has the mask "has the same value" it means that that option value is compliant only if all the
            ITestContext within the list share the same value. This clearly depends on the single value of all the text contexts,
            not only on the given one

        :param i: the index of test context we're dealing with inside `actual_set`
        :param actual: the value of the option of the test context we're dealing with
        :param actual_set: the sert of all the test contexts we're dealing with
        :return: True if this option mask is compliant: this means that the value of the option has passed a constraint.
        """
        pass


class ITestContextRepo(abc.ABC):
    """
    Reprepsents a collection of test context which can you easily query via a mask

    The main method is query_by_mask allowing to query for compliant test contexts
    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def append(self, v: "ITestContext"):
        """
        adds a new ITestContext in the repository
        :param v: the new test to add
        :return: nothing
        """
        pass

    @abc.abstractmethod
    def __iter__(self) -> Iterable[ITestContext]:
        """
        all the test contexts in the repo

        order is not garantueed at all

        :return: iterable of all the ITestContext within the repo
        """
        pass

    @abc.abstractmethod
    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        """
        Generate a view (aka a sublist) containing all the ITestContext which are both in the repo and are compliant
        with the mask you've passed
        :param m: the mask we need to check to determine if a test context is compliant
        :return: a view of all the compliant test contexts
        """
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        """

        :return: number of element inside this repo
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """
        remove all the ITestContext inside this repo
        :return: nothing
        """
        pass

    def __str__(self) -> str:
        return "{" + "\n".join(map(str, self)) + "}"


class ITestContextRepoView(abc.ABC):

    @abc.abstractmethod
    def __iter__(self) -> Iterable[ITestContext]:
        pass

    @abc.abstractmethod
    def __getitem__(self, item: int) -> "ITestContext":
        pass

    @property
    @abc.abstractmethod
    def repository(self) -> "ITestContextRepo":
        pass

    @abc.abstractmethod
    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        pass

    def __str__(self) -> str:
        return "{" + "\n".join(map(str, self)) + "}"


class IDataSourceListener(abc.ABC):
    """
    Allows you to react to updates in the data source
    """

    @abc.abstractmethod
    def on_new_data_added(self, path: str, name: str):
        pass


class IResourceManager(abc.ABC):
    """
    A class which allows to read/write a resource with a well specified type in a well specified data source
    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        """
        Determine if this resource manager can be attached to the specified datasource
        :param datasource: the datasource to check
        :return: true if we can register this resource manager to `datasource`, false otherwise
        """
        pass

    @abc.abstractmethod
    def can_handle_data_type(self, datasource: "IDataSource", data_type: str) -> bool:
        """
        :param datasource: the data source we will operate on
        :param data_type: the data_type of resource we need to check if this resource manager can effectively handle
        :return: true if this resaource manager can handle `data_type`
        """
        pass

    @abc.abstractmethod
    def _on_attached(self, datasource: "IDataSource"):
        """
        Code executed when the resource manager is registered to a particular datasource
        :param datasource: the datasoruce we have jsut attached to
        :return:
        """
        pass

    @abc.abstractmethod
    def save_at(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str, content: Any):
        """
        Upload a resource in the filesystem to the datasource by setting to a particular path

        If the resources already exists, the function will overwrites it.
        If the path was never used up until now, the function behaves normally.

        :param datasource: the data source we will operate on
        :param path: the path where we need to upload it
        :param ks001: the name of the file to save into the datasource
        :param data_type: the type fo the data to upload.
        :param content: the content to upload to the data source. The exact content highly depend on the resource
        :return:
        """
        pass

    @abc.abstractmethod
    def get(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Any:
        """
        get the content of a particular file

        :param datasource: the data source we will operate on
        :param path: path of the file to load
        :param ks001: name of the resource to load. Resources need ot be in KS001 format
        :param data_type: type of file to load
        :raises ResourceNotFoundError: if the resources was not present in the datasource
        :return:
        """
        pass

    @abc.abstractmethod
    def get_all(self, datasource: "IDataSource", path: str = None, data_type: str = None) -> Iterable[Tuple[str, str, str]]:
        """
        get all the resources which are in `path` and have type `data_type`

        :param datasource: the data source we will operate on
        :param path: the path where to look for resources in the datasource.
            If None we will look over all the datasource
        :param data_type: the type of the data we're looking for in the dartasource.
            If Nnone we will look oiver all the datasource
        :return: an iterable of path, ks001 and data_type of every resource compliant with the request
        """
        pass

    @abc.abstractmethod
    def contains(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> bool:
        """
        Check if a resource exists in the data source

        Function works even when this instance of path is used for the first time

        :param datasource: the data source we will operate on
        :param path: the path of the resource
        :param ks001: the name of the resource. name must be compliant with KS001 format
        :param data_type: type of the resource to check
        :return: true if the datasource has a resource as specified, false otherwise
        """
        pass

    @abc.abstractmethod
    def remove(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str):
        """
        Removes a resource in the data source

        The function works even when this instance of path is used for the first time

        :param datasource: the data source we will operate on
        :param path: the path of the resource
        :param ks001: the name of the resource. name must be compliant with KS001 format
        :param data_type: type of the resource to remove
        :raises ResourceNotFoundError: if the resaource does not exist
        :return:
        """
        pass

    @abc.abstractmethod
    def iterate_over(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Iterable[Any]:
        """
        Open the resource specified and than perform an iteration of such resource.

        The semantic of the implementation depends on the resource type loaded.

        For large resources this method may improve memory footprint

        :param datasource: the data source we will operate on
        :param path: the path of the resource to open
        :param ks001: the ks001 of the resource to open
        :param data_type: the data type fo the resource to open
        :return:
        """


class ICsvResourceManager(IResourceManager, abc.ABC):
    """
    A manager which handle the "csv" resources
    """

    def __init__(self):
        IResourceManager.__init__(self)

    @abc.abstractmethod
    def head(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def tail(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> Dict[str, Any]:
        pass

    def first(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Dict[str, Any]:
        return self.head(datasource, path, ks001, data_type, 1)

    def last(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Dict[str, Any]:
        return self.tail(datasource, path, ks001, data_type, 1)


class IDataSource(abc.ABC):
    """
    Represents a place where experimental data can be gathered from.

    This may be the file system or even a database.


    Within a tester datasource, there are several "files", which represents raw data in a unspecified form.
    To discern file content, each "file" has a "type".
    Each "file" has a name and can be fetched inside a "path". a "path" is a string separated by the special
    character '/' which separates between different subgroups. Intend "path" as a way to implement a organized tree-like
    document structure. "file" name **always** is encoded via KS001
    standard. "files" have unique triple or "path", "name" and "type".

    Use
    ===

    Data sources are intended to be used in a "with" statement:

    with DataSourceImpl() as datasource:
        datasource.save_generic_data_at(...)

    """

    def __init__(self):
        """
        Initialize the Datasource.
        """
        self.listeners = []
        self.resource_managers: Dict[str, "IResourceManager"] = {}

    @abc.abstractmethod
    def __enter__(self) -> "IDataSource":
        """
        Allocate resources necessary to run the data source
        :return: self
        """
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Deallocate resources necessary to run the data source
        """
        pass

    @abc.abstractmethod
    def name(self):
        """
        name of the data source. Used to informally indicate the datasource
        :return: the name of datasource
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """
        Completely remove everything inside this datasource

        This will remove all the data in the datasource
        :return:
        """
        pass

    def get_manager_of(self, data_type: str) -> "IResourceManager":
        """
        Get the manager responsible of handling resources of type `data_type`
        :param data_type:
        :return:
        """
        return self.resource_managers[data_type]

    def save_at(self, path: str, ks001: KS001Str, data_type: str, content: Any):
        """
        Upload a file in the filesystem to the datasource by setting to a particular path

        If the resources already exists, the function will overwrites it.
        If the path was never used up until now, the function behaves normally.

        :param path: the path where we need to upload it
        :param ks001: the name of the file to save into the datasource
        :param data_type: the type fo the data to upload.
        :param content: the content to upload to the database (as is, raw)
        :return:
        """
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        self.resource_managers[data_type].save_at(self, path, ks001, data_type, content)

    def get(self, path: str, ks001: KS001Str, data_type: str) -> Any:
        """
        get the content of a particular file
        :param path: path of the file to load
        :param ks001: name of the resource to load. Resources need ot be in KS001 format
        :param data_type: type of file to load
        :raises ResourceNotFoundError: if the resources was not present in the datasource
        :return:
        """
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        return self.resource_managers[data_type].get(self, path, ks001, data_type)

    def get_all(self, path: str = None, data_type: str = None) -> Iterable[Tuple[str, str, str]]:
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        return self.resource_managers[data_type].get_all(self, path, data_type)

    def contains(self, path: str, ks001: KS001Str, data_type: str) -> bool:
        """
        Check if a resource exists

        Function works even when this instance of path is used for the first time

        :param path: the path of the resource
        :param ks001: the name of the resource. name must be compliant with KS001 format
        :param data_type: type of the resource to check
        :return: true if the datasource has a resource as specified, false otherwise
        """
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        return self.resource_managers[data_type].contains(self, path, ks001, data_type)

    def remove(self, path: str, ks001: KS001Str, data_type: str):
        """
        Removes a resource in the data source

        The function works even when this instance of path is used for the first time

        :param path: the path of the resource
        :param ks001: the name of the resource. name must be compliant with KS001 format
        :param data_type: type of the resource to remove
        :raises ResourceNotFoundError: if the resaource does not exist
        :return:
        """
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        self.resource_managers[data_type].remove(self, path, ks001, data_type)

    # @abc.abstractmethod
    # def save_csv_at(self, path: str, ks001: KS001Str, content: str):
    #     """
    #     Upload a csv in the data source
    #
    #     If the resources already exists, the function will overwrites it.
    #     If the path was never used up until now, the function behaves normally.
    #
    #     :param path: path in the datasource where you want to save the csv to
    #     :param ks001: the name of the resources we want to generate
    #     :param content: the content of the resource we want to generate
    #
    #     :return:
    #     """
    #     # self.save_generic_data_at(csv_filename, path=path, data_type=data_type)
    #     pass

    # @abc.abstractmethod
    # def get_csv(self, path: str, ks001: KS001Str) -> str:
    #     """
    #     get a csv string content from the datasource
    #     :param path: the path where to fetch the csv
    #     :param ks001: the name of the resource we want to load
    #     :raises ResourceNotFoundError: if the resources was not present in the datasource
    #     :return: the string containing the csv file content
    #     """
    #     pass

    def iterate_over(self, path: str, ks001: KS001Str, data_type: str) -> Iterable[Any]:
        """
        Open the resource specified and than perform an iteration of such resource.

        The semantic of the implementation depends on the resource type loaded

        :param path: the path of the resource to open
        :param ks001:
        :param data_type:
        :return:
        """
        if data_type not in self.resource_managers:
            raise ResourceTypeUnhandledError(f"{data_type} is not handled by {self.name()}")

        yield from self.resource_managers[data_type].iterate_over(self, path, ks001, data_type)

    def get_suchthat(self,
                            filters: List[ICsvFilter] = None,
                            test_context_template: "ITestContext" = None,
                            path: str = None, data_type: str = None,
                            force_generate_ks001: bool = False, force_generate_textcontext: bool = False) -> Iterable[GetSuchInfo]:
        """
        get all the csv data in the datasource which follows the condition

        path and data_type can be optionally specifiy to statically reduce the number of resources involved while
        searching
        :param filters: filters which consider only a subset of csvs
        :param test_context_template: a ITestContext which we will use to clone to
        :param path: path used to consider only a subset of all the resources in the datasource. If None we will
            consider all the resources in the datasource
        :param data_type: data_type used to consider only a subset of all the resources in the datasource. If None we
            will consider all the resources in the datasource.
        :param force_generate_ks001: if true we generate for each csv which surpass all the filters the KS001 structure.
            If False we will generate such structure only if strictly needed.
        :param force_generate_textcontext: if true we will generate for each csv which surpasses all the filter the
            TestContext structure. If False we will generate it only if strictly needed.
        :return:
        """

        # TODO rename csv in "generic data"
        filters = filters if filters is not None else []
        naive_csv_filters: List[INaiveCsvFilter] = list(filter(lambda f: f.is_naive(), filters))
        single_csv_filters: List[ISingleCsvFilter] = list(filter(lambda f: f.is_single(), filters))
        test_context_csv_filters: List[ITestContextCsvFilter] = list(filter(lambda f: f.is_testcontext(), filters))
        complex_csv_filters: List[IComplexCsvFilter] = list(filter(lambda f: f.is_complex(), filters))

        has_naive_filters = len(naive_csv_filters) > 0
        has_single_filters = len(single_csv_filters) > 0
        has_testcontext_filters = len(test_context_csv_filters) > 0
        has_complex_filters = len(complex_csv_filters) > 0

        if test_context_template is None and (has_single_filters or has_testcontext_filters or has_complex_filters):
            raise ValueError(f"rtest context template is None but we strictly require it since you have specified either a single filter or a complex one!")

        def handle_generic_data(i: int, path: str, ks001str: str, data_type: str) -> Tuple[bool, Optional["ITestContext"], Optional["KS001"], Optional[str]]:
            logging.debug(f"considering {path}/{ks001str} (type={data_type})...")
            if not has_naive_filters and not has_single_filters and not has_testcontext_filters and not has_complex_filters:
                # if there are no filters we accept everything!
                return True, None, None, data_type

            for cf in naive_csv_filters:
                if not cf.is_valid(path, ks001str, data_type, i):
                    return False, None, None, None

            if not has_single_filters and not has_testcontext_filters and not has_complex_filters:
                # if, aside naive filters, there are no filters, we accept everything
                return True, None, None, data_type

            logging.debug(f"checking csv #{i}")
            # logging.info(f"considering csv #{i}")
            # we check if the csv filename is compliant with our filter
            # we know the relevant csvs have as their first dict of the filename
            # the encoding of the relevant test context
            tc = test_context_template.clone()

            # we test if the csv fetched has its KS001 compliant with a general one. This because
            # test context is a KS001, but it does NOT contain all the key-values a normal KS001 may.
            # test context is just ONE dictionary in the KS001, while KS001 contains several dictionaries
            csv_filename_ks001 = KS001.parse_str(
                string=ks001str,
                key_alias=tc.key_alias,
                value_alias=tc.value_alias,
                colon=constants.SEP_COLON,
                pipe=constants.SEP_PIPE,
                underscore=constants.SEP_PAIRS,
                equal=constants.SEP_KEYVALUE,
            )

            for f in single_csv_filters:
                if not f.is_valid(path, ks001str, csv_filename_ks001, data_type, i):
                    # this csv doesn't satisfy the filter
                    return False, None, None, None

            if not has_testcontext_filters and not has_complex_filters:
                # if, aside naive filters and single one there are not filters we return immediately
                return True, None, csv_filename_ks001, data_type

            tc.set_from_ks001_index(
                index=0,
                ks=csv_filename_ks001
            )

            for f in test_context_csv_filters:
                if not f.is_valid(path, ks001str, data_type, csv_filename_ks001, tc, i):
                    return False, None, None, None

            # the csv contains values which we're interested in?
            # FIXME if the user doesn't reuse the same output direcotry for multiple run with different sutff under test/test environment this is useless
            # if not tc.are_option_values_all_in(research_factory.under_test_dict_values, research_factory.test_environment_dict_values):
            #    return False, None, None, None

            return True, tc, csv_filename_ks001, data_type

        test_context_from_csv_filename_list: List[GetSuchInfo] = []
        for i, (path, ks001str, data_type) in enumerate(self.get_all(path, data_type)):
            outcome, tc, ks001, dt = handle_generic_data(i, path, ks001str, data_type)
            if outcome:

                if not has_complex_filters:
                    # if aside from naive and single filters, there are no other fgilters, we accept everything
                    # NOTE: when there are no complex filter there is no use for test_context_from_csv_filename_list
                    # so we avoid it altogether
                    if force_generate_ks001 and ks001 is None:
                        ks001 = KS001.parse_str(
                            string=ks001str,
                            key_alias=test_context_template.key_alias,
                            value_alias=test_context_template.value_alias,
                            colon=constants.SEP_COLON,
                            pipe=constants.SEP_PIPE,
                            underscore=constants.SEP_PAIRS,
                            equal=constants.SEP_KEYVALUE,
                        )
                    if force_generate_textcontext and tc is None:
                        tc = test_context_template.clone()
                        tc.set_from_ks001_index(0, ks001)
                    yield GetSuchInfo(path, ks001str, data_type, ks001, tc)
                else:
                    # ok, there are some complex filters. We need to populate test_context_from_csv_filename_list.
                    # ok we may add this new csv. Of course we still need to check if it surpasses the checks of the complex
                    # masks, but then again, we need the whole set in order to compute those!
                    logging.debug(f"got a new csv {ks001str}! length is {len(test_context_from_csv_filename_list)}!")
                    test_context_from_csv_filename_list.append(GetSuchInfo(path, ks001str, data_type, ks001, tc))

        if has_complex_filters:
            # we check the complex filters only if they are present

            # we store the test_contexts in a list because some masks may need the whole list of text_contexts handle to
            # decide if an option value is compliant or not
            for i, (path, ks001str, data_type, csv_ks001, test_context) in enumerate(test_context_from_csv_filename_list):

                logging.debug(f"check compliance!")
                logging.debug(f"val : {test_context}")

                valid = True
                for cf in complex_csv_filters:
                    if not cf.is_valid(path, ks001str, csv_ks001, data_type, i, test_context_from_csv_filename_list):
                        valid = False
                        break
                if not valid:
                    continue

                logging.debug(f"is compliant!")
                # we know for sure that both csv_ks001 and test_context are not None
                yield GetSuchInfo(path, ks001str, data_type, csv_ks001, test_context)

    # @abc.abstractmethod
    # def contains_csv(self, path: str, ks001: KS001Str) -> bool:
    #     """
    #     Check if a csv resource exists
    #
    #     Function works even when this instance of path is used for the first time
    #
    #     :param path: the path of the resource
    #     :param ks001: the name of the resource. name must be compliant with KS001 format
    #     :return: true if the datasource has a resource as specified, false otherwise
    #     """
    #     pass
    #
    # @abc.abstractmethod
    # def remove_csv(self, path: str, ks001: KS001Str):
    #     """
    #     Removes a resource in the data source
    #
    #     The function works even when this instance of path is used for the first time
    #
    #     :param path: the path of the resource
    #     :param ks001: the name of the resource. name must be compliant with KS001 format
    #     :raises ResourceNotFoundError: if the resaource does not exist
    #     :return:
    #     """
    #     pass

    def transfer_to(self, other: "IDataSource", from_path: str, from_ks001: KS001Str, from_data_type: str, to_path: str = None, to_ks001: KS001Str = None, to_data_type: str = None, remove: bool = False):
        """
        Transfer the resource from the current data source to another one. You can optionally specify
        new path, data type and ks001 in the target data source.

        The function is garantueed to do nothing if self is equal to other and
        the start position ids the same of end position

        :param other: the other datasource that will receive the resources from the current one
        :param from_path: the path of the resource to transfer in self
        :param from_ks001: the name of the reosurce to trasnfer in self
        :param from_data_type: the type of the resource to transfer in self
        :param to_path: the path the transferred resource will have in the other datasource. If None it will be
            the same as before
        :param to_ks001: the name the transferred resource will have in the other datasource. If None it will be
            the same as before
        :param to_data_type: the data type the transferred resource will have in the other datasource. If None it will be
            the same as before
        :param remove: if True we will remove the resource from "self" datasource. Otherwise the resource will be
            copied "as is"
        :raises ResourceNotFoundError: if the resource does not exist in the current data source
        :return:
        """
        to_path = to_path or from_path
        to_ks001 = to_ks001 or from_ks001
        to_data_type = to_data_type or from_data_type
        if self == other and from_path == to_path and from_ks001 == to_ks001 and from_data_type == to_data_type:
            return

        generic_data = self.get(path=from_path, ks001=from_ks001, data_type=from_data_type)
        if remove:
            self.remove(from_path, from_ks001, from_data_type)

        other.save_at(to_path, to_ks001, to_data_type, generic_data)

    # def transfer_csv_to(self, other: "IDataSource", from_path: str, from_ks001: KS001Str,
    #                          to_path: str = None, to_ks001: KS001Str = None, remove: bool = False):
    #     """
    #     Transfer the csv resource from the current data source to another one. You can optionally specify
    #     new path and ks001 in the target data source.
    #
    #     The function is garantueed to do nothing if self is equal to other and
    #     the start position ids the same of end position
    #
    #     :param other: the other datasource that will receive the resources from the current one
    #     :param from_path: the path of the resource to transfer in self
    #     :param from_ks001: the name of the reosurce to trasnfer in self
    #     :param to_path: the path the transferred resource will have in the other datasource. If None it will be
    #         the same as before
    #     :param to_ks001: the name the transferred resource will have in the other datasource. If None it will be
    #         the same as before
    #     :param remove: if True we will remove the resource from "self" datasource. Otherwise the resource will be
    #         copied "as is"
    #     :raises ResourceNotFoundError: if the resource does not exist in the current data source
    #     :return:
    #     """
    #     to_path = to_path or from_path
    #     to_ks001 = to_ks001 or from_ks001
    #     if self == other and from_path == to_path and from_ks001 == to_ks001:
    #         return
    #
    #     csv_content = self.get_csv(path=from_path, ks001=from_ks001)
    #     if remove:
    #         self.remove_csv(from_path, from_ks001)
    #
    #     other.save_csv_at(to_path, to_ks001, csv_content)

    def move_to(self, other: "IDataSource", from_path: str, from_ks001: KS001Str, from_data_type: str,
                             to_path: str = None, to_ks001: KS001Str = None):
        """
        Shortcut for transfer_csv_to  with remove set to True
        :param other:
        :param from_path:
        :param from_ks001:
        :param to_path:
        :param to_ks001:
        :return:
        """
        self.transfer_to(other=other,
                         from_path=from_path, from_ks001=from_ks001, from_data_type=from_data_type,
                         to_path=to_path, to_ks001=to_ks001, to_data_type=from_data_type, remove=True
                         )

    def copy_to(self, other: "IDataSource", from_path: str, from_ks001: KS001Str, from_data_type: str,
                    to_path: str = None, to_ks001: KS001Str = None):
        """
        Shortcut for transfer_csv_to  with remove set to False

        :param other:
        :param from_path:
        :param from_ks001:
        :param to_path:
        :param to_ks001:
        :return:
        """
        self.transfer_to(other=other,
                         from_path=from_path, from_ks001=from_ks001, from_data_type=from_data_type,
                         to_path=to_path, to_ks001=to_ks001, to_data_type=from_data_type,
                         remove=False
                        )

    def move_to_suchthat(self,
                              other: "IDataSource",
                              from_path: str,
                              data_type: str = None, to_path: str = None,
                              filters: List[ICsvFilter] = None,
                              test_context_template: "ITestContext" = None):
        for getsuchinfo in self.get_suchthat(
                test_context_template=test_context_template, filters=filters,
                path=from_path, data_type=data_type):
            self.move_to(other, getsuchinfo.path, getsuchinfo.name, getsuchinfo.type, to_path)

    def copy_to_suchthat(self,
                              other: "IDataSource",
                              from_path: str,
                              data_type: str = None, to_path: str = None,
                              filters: List[ICsvFilter] = None,
                              test_context_template: "ITestContext" = None):
        for getsuchinfo in self.get_suchthat(
                test_context_template=test_context_template, filters=filters,
                path=from_path, data_type=data_type):
            self.copy_to(other, getsuchinfo.path, getsuchinfo.name, to_path)

    def remove_suchthat(self,
                                from_path: str,
                                data_type: str = None,
                                filters: List[ICsvFilter] = None,
                                test_context_template: "ITestContext" = None):
        for getsuchinfo in self.get_suchthat(
                test_context_template=test_context_template, filters=filters,
                path=from_path, data_type=data_type):
            self.remove(getsuchinfo.path, getsuchinfo.name, data_type)

    def register_resource_manager(self, resource_type: str, manager: "IResourceManager"):
        self.resource_managers[resource_type] = manager
        manager._on_attached(self)

    def unregister_resource_manager(self, resource_type: str):
        del self.resource_managers[resource_type]

    def unregister_all_resource_managers(self):
        self.resource_managers = {}

    def add_datasource_listener(self, listener: "IDataSourceListener"):
        self.listeners.append(listener)

    def clear_listeneres(self):
        self.listeners.clear()
