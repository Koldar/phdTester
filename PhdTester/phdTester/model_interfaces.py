import abc
import enum
from abc import ABC
from typing import Any, Tuple, Iterable, Dict, List

from phdTester import constants
from phdTester.graph import ISingleDirectedGraph
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


class IDependencyCondition(abc.ABC):

    @property
    @abc.abstractmethod
    def kind(self) -> ConditionKind:
        """
        Type of condition
        :return:
        """
        pass

    @abc.abstractmethod
    def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        """
        check if we should check the compliance of this condition

        :param graph: the graph containing source_name and sink_name
        :param source_name: the source vertex of the condition
        :param sink_name: the sink vertex of the condition
        :param tc: the test context
        :return: true if we should check the accept method of this edge and follow this edge), false if the text
        context is not applicable to
        this edge
        """
        pass

    @abc.abstractmethod
    def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        """
        Check if this constraint is valid

        :param graph: the graph containing the whole contraints
        :param source_name: name of the source node of this constraint
        :param sink_name: name of the sink node of this constraint
        :param tc: test context we're applying the constraint to
        :return: true if `tc` satisfies this constraint, false otherwise
        """
        pass


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

    Values can be set to None

    You use this interface to allow you to let you implement all the methods without any fields.
    In this terminology, the keys are said **options**
    """

    def __init__(self):
        pass

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


class ICsvRow(abc.ABC):

    def __init__(self):
        pass


class IUnderTesting(IOptionDictWithKS, ILabelable, ABC):
    """
    An under testing reperesents the element you want to test within a ITestContext

    This structure may contains several options. The options values can be None.
    """

    def __init__(self):
        IOptionDictWithKS.__init__(self)
        ILabelable.__init__(self)


class ITestingEnvironment(IOptionDictWithKS, ILabelable, ABC):

    def __init__(self):
        IOptionDictWithKS.__init__(self)
        ILabelable.__init__(self)

    @abc.abstractmethod
    def get_order_key(self) -> str:
        """

        :return: a string generated for order several test environment
        """


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

    def is_complaint_with_test_context(self, tc: "ITestContext", tcs: List["ITestContext"]) -> bool:
        """
        Check if a test context is compliant against the given mask

        :param tc: the test context we need to check
        :param tcs: a list of test context which are interepreted as the "test context pool". Some masks in order
            to correctly operates needs to check the value of an option of a test context not singularly, but related
            to a list of other test contexts. It is required that `tc` belongs to `tcs`
        :return: True if `tc` is compliant with the given mask, `False` otherwise
        """
        i = tcs.index(tc)
        for o in self.options():
            expected: ITestContextMaskOption = self.get_option(o)
            actual = tc.get_option(o)
            if expected is None:
                continue
            if not expected.is_compliant(i, actual, tcs):
                return False
        return True

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


class Function2D(abc.ABC):
    """
    Represents a function y=f(x). The function is merely a set of 2D points, so it's more like a mapping.
    Functions have no names
    """

    def __init__(self):
        self._function = {}

    @classmethod
    def from_xy(cls, x: Iterable[float], y: Iterable[float]) -> "Function2D":
        """
        Create a new function from 2 lists of the same length
        :param x: the x values
        :param y: the y values
        :return: a new function
        """
        result = cls()
        for x, y in zip(x, y):
            result[x] = y
        return result

    def update_point(self, x: float, y: float):
        """
        adds a point in the function.
        If the value was already present the old value is overwritten

        :param x: the x vlaue to add
        :param y: the y value to add
        """
        self._function[x] = y

    def get_y(self, x: float) -> float:
        """

        :param x: the x value whose y value we need to fetch
        :return: the y value associated to the x value
        """
        return self._function[x]

    def x_unordered_values(self) -> Iterable[float]:
        """

        :return: iterable of x values. Order is **not** garantueed
        """
        return self._function.keys()

    def keys(self) -> Iterable[float]:
        """

        :return: alias of x_unordered_values
        """
        return self.x_unordered_values()

    def x_ordered_values(self) -> Iterable[float]:
        """

        :return: iterable of x values. Order goes from the lowest till the greatest
        """
        return sorted(self._function.keys())

    def y_unordered_value(self) -> Iterable[float]:
        """

        :return: iterable of y values. Order is **not** garantueed
        """
        return self._function.values()

    def y_ordered_value(self) -> Iterable[float]:
        """

        :return: iterable of y values. Order is garantueed
        """
        return sorted(self._function.values())

    def xy_unordered_values(self) -> Iterable[Tuple[float, float]]:
        """

        :return: iterable of pair os x,y. Order is **not** garantueed
        """
        return self._function.items()

    def __contains__(self, item: float) -> bool:
        """

        :param item: the x vcalue to check
        :return: true if a x value is present in the function, false otherwise
        """
        return item in self._function

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

    @property
    def dict(self) -> Dict[float, float]:
        return self._function


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


class IAggregator(abc.ABC):
    """
    Represents an object which merge different number in order to maintain a specific metric.

    For example, a mean aggregator keeps accepting a stream of number and maintains the average of
    the online succession
    """

    # TODO remove None from new
    @abc.abstractmethod
    def first_value(self, new: float = None) -> float:
        """
        Actions to perform when the very first element of the sequence arrives
        :param new: the first element of the sequence
        :return: the measurement you want to keep track of after the first element of the sequence has been received
        """
        pass

    @abc.abstractmethod
    def aggregate(self, old: float, new: float) -> float:
        """
        Actions to perform when a new element of the sequence arrives

        For example assume you want to maintain the maximum of a sequence. Right now you have
        the maximum set to 6. Then you receive 3. 6 will be "old", 3 will be "new" and the function should return 6
        (the maximum of a sequence whose maximum is 6 and 3 is still 6).
        If you then received another value 9 the new maximum will be 9.

        :param old: the value of the measurement you want to maintain before the new value was detected
        :param new: the new value to accept
        :return: the value of the measurement you want to maintain after having received the new value
        """
        pass


class ICurvesChanger(abc.ABC):
    """
    Curve changers are objects which take in input the set of curves you need to plot inside a single graph
    and perform some operation on it.

    Curves changer are extremely useful when you want to tweak a a plot by doing something trivial.
    For example they can be used to add new generated curves, or remove peaks.
    """

    @abc.abstractmethod
    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        """
        perform the operation altering the curves
        :param curves: the curves to alter
        :return: a new set of functions to plot
        """
        pass


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

    @abc.abstractmethod
    def __str__(self) -> str:
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
