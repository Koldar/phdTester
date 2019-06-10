import math
import re
from typing import Any, Iterable, List

from phdTester import commons
from phdTester.model_interfaces import ITestContextMaskOption, ITestContext, ITestEnvironment, \
    ISimpleTestContextMaskOption, IComplexTestContextMaskOption, ITestContextMask


class MutHaveDynamicallyChosenValue(ISimpleTestContextMaskOption):
    """
    An option is compliant if it has the same value as the one generated in a previous computation.

    This option mask is similar but very different than MustHaveValue:
    MustHaveValue says that the value of the option needs to be static, while this one
    has avalue that may change during the same computation.
    """

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, MutHaveDynamicallyChosenValue)

    def represents_a_well_specified_value(self) -> bool:
        return self.can_operate

    def get_well_specified_value_as_string(self) -> str:
        if not self.represents_a_well_specified_value():
            raise ValueError(f"does not represent a value")
        return str(self.value)

    def get_well_specified_value(self) -> Any:
        if not self.represents_a_well_specified_value():
            raise ValueError(f"does not represent a value")
        return self.value  # make value private or protected

    def __init__(self):
        ITestContextMaskOption.__init__(self)
        self._can_operate = False
        self._value = None

    def set_params(self, **kwargs):
        if all(map(lambda x: x in kwargs, ["current_test_environment", "option_name"])):
            ctd: "ITestEnvironment" = kwargs["current_test_environment"]
            option_name: str = kwargs["option_name"]

            self._value = ctd.get_option(option_name)
            self._can_operate = True
        else:
            self._can_operate = False

    @property
    def can_operate(self) -> bool:
        return self._can_operate

    @property
    def value(self) -> Any:
        if not self._can_operate:
            raise ValueError(f"mask cannot be operated!")
        return self._value

    def is_compliant(self, actual: "Any") -> bool:
        if self._value is None:
            return False
        else:
            return self._value == actual

    def __str__(self) -> str:
        if self._can_operate:
            if self._value is not None:
                return f"needs not to be None"
            else:
                return f"needs to be {self._value}"
        else:
            return f"needs to be of a value dynamically obtained"


class TestContextSetMustBeConstant(IComplexTestContextMaskOption):
    """
    An option value is compliant only if over a certain set remains the same
    """

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, TestContextSetMustBeConstant)

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"does not specify a value")

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"does not represent anything")

    def __init__(self):
        ITestContextMaskOption.__init__(self)

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        value = actual_set[0]

        for el in actual_set[1:]:
            if el != value:
                return False
        else:
            return True

    def __str__(self):
        return "has to be the same over a set"


class CannotBeNull(ISimpleTestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if it's not null
    """

    def __init__(self):
        ITestContextMaskOption.__init__(self)

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, CannotBeNull)

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"does not specify a value")

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"does not represent anything")

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        return actual is not None

    def __str__(self):
        return "has not to be null"


class MustHaveValue(ISimpleTestContextMaskOption, commons.SlottedClass):
    """
    A concrete option value is compliant with this mask only if it has a very well specific value
    """

    __slots__ = ('__value', )

    def __init__(self, value: Any):
        ITestContextMaskOption.__init__(self)
        self.__value = value

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, MustHaveValue) and self.__value == other.__value

    def represents_a_well_specified_value(self) -> bool:
        return True

    def get_well_specified_value_as_string(self) -> str:
        return str(self.__value)

    def get_well_specified_value(self) -> Any:
        return self.__value

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        # if the comparison is against floating point number, the comparison may become fuzzy.
        # We handle such special case
        if isinstance(actual, float):
            return math.isclose(actual, self.__value)
        else:
            return actual == self.__value

    def __str__(self):
        return f"has to be {self.__value}"


class CannotHaveValue(ISimpleTestContextMaskOption):
    """
    Option compliant with this mask are required not to be equal to a given value.

    This in practice implement the operation x != k
    """

    def __init__(self, value: Any):
        ITestContextMaskOption.__init__(self)
        self.value = value

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, CannotHaveValue) and self.value == other.value

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"doesn't specify a value")

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"doesn't specify a value")

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        # if the comparison is against floating point number, the comparison may become fuzzy.
        # We handle such special case
        if isinstance(actual, float):
            return not math.isclose(actual, self.value)
        else:
            return actual != self.value

    def __str__(self) -> str:
        return f"can't have value {self.value}"


class HasToMatchPattern(ISimpleTestContextMaskOption):
    """
    A concrete option value is compliant with this mask only its its string representation follow a specified regex
    """

    def __init__(self, regex: str):
        ITestContextMaskOption.__init__(self)
        self._regex = regex

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, HasToMatchPattern) and self._regex == other._regex

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"doesn't specify a value")

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"doesn't specify a value")

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        return actual is not None and re.match(self._regex, str(actual)) is not None

    def __str__(self) -> str:
        return f"needs to match regex \"{self._regex}\""


class MustBeInSet(ISimpleTestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if its value is inside a well specified set
    """

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, MustBeInSet) and other.values == self.values

    def represents_a_well_specified_value(self) -> bool:
        return True

    def get_well_specified_value_as_string(self) -> str:
        return ", ".join(map(str, self.values))

    def get_well_specified_value(self) -> Any:
        return self.values  # make values private ro protected

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def __init__(self, values: Iterable[Any]):
        ITestContextMaskOption.__init__(self)
        self.values = list(values)

    def is_compliant(self, actual: "Any") -> bool:
        return actual in self.values

    def __str__(self):
        return "has to be in [{}]".format(', '.join(map(str, self.values)))


class CannotBeInSet(ISimpleTestContextMaskOption):

    def __init__(self, prohibited_set: List[Any]):
        self.prohibited_set = prohibited_set

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, CannotBeInSet) and self.prohibited_set == other.prohibited_set

    def is_compliant(self, actual: "Any") -> bool:
        return actual not in self.prohibited_set

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"doesn't specify a value")

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"doesn't specify a value")

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def __str__(self) -> str:
        return "has not to be in [{}]".format(', '.join(map(str, self.prohibited_set)))


class Ignore(ISimpleTestContextMaskOption):
    """
    A concrete option value is always compliant with this mask
    """

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, Ignore)

    def represents_a_well_specified_value(self) -> bool:
        return False

    def get_well_specified_value_as_string(self) -> str:
        raise ValueError(f"does not represent anything")

    def get_well_specified_value(self) -> Any:
        raise ValueError(f"does not represent anything")

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        return True

    def __str__(self):
        return "ignore"


class HasToBeNull(ISimpleTestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if it is null
    """

    def __eq__(self, other: "ITestContextMask") -> bool:
        return isinstance(other, HasToBeNull)

    def represents_a_well_specified_value(self) -> bool:
        """
        this is abit weird. we need it to be None.

        However we exploit this when generating the subtitle
        :return:
        """
        return True

    def get_well_specified_value_as_string(self) -> str:
        return "None"

    def get_well_specified_value(self) -> Any:
        return None

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def is_compliant(self, actual: "Any") -> bool:
        return actual is None

    def __str__(self):
        return "has to be null"
