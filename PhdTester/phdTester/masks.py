import re
from typing import Any, Iterable, List

from phdTester.model_interfaces import ITestContextMaskOption, ITestContext, ITestingEnvironment


class TestContextMaskNeedsToBeSameAsNonComputation(ITestContextMaskOption):
    """
    An option is compliant if it has the same value as the one generated in a previous computation.

    This option mask is similar but very different than TestContextMaskNeedToHaveValue:
    TestContextMaskNeedToHaveValue says that the value of the option needs to be static, while this one
    has avalue that may change during the same computation.
    """

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
            ctd: "ITestingEnvironment" = kwargs["current_test_environment"]
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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
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


class TestContextMaskNeedsToBeTheSameOverSet(ITestContextMaskOption):
    """
    An option value is compliant only if over a certain set remains the same
    """

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


class TestContextMaskNeedsNotNull(ITestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if it's not null
    """

    def __init__(self):
        ITestContextMaskOption.__init__(self)

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual is not None

    def __str__(self):
        return "has not to be null"


class TestContextMaskNeedToHaveValue(ITestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if it has a very well specific value
    """

    def represents_a_well_specified_value(self) -> bool:
        return True

    def get_well_specified_value_as_string(self) -> str:
        return str(self.value)

    def get_well_specified_value(self) -> Any:
        return self.value  # TODO make value private or protected

    def set_params(self, **kwargs):
        pass

    @property
    def can_operate(self) -> bool:
        return True

    def __init__(self, value: Any):
        ITestContextMaskOption.__init__(self)
        self.value = value

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual == self.value

    def __str__(self):
        return f"has to be {self.value}"


class TestContextMaskNeedsNotToHaveValue(ITestContextMaskOption):
    """
    Option compliant with this mask are required not to be equal to a given value.

    This in practice implement the operation x != k
    """

    def __init__(self, value: Any):
        ITestContextMaskOption.__init__(self)
        self.value = value

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual != self.value

    def __str__(self) -> str:
        return f"can't have value {self.value}"


class TestContextMaskNeedsToFollowPattern(ITestContextMaskOption):
    """
    A concrete option value is compliant with this mask only its its string representation follow a specified regex
    """

    def __init__(self, regex: str):
        ITestContextMaskOption.__init__(self)
        self._regex = regex

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual is not None and re.match(self._regex, str(actual)) is not None

    def __str__(self) -> str:
        return f"needs to match regex \"{self._regex}\""


class TestContextMaskNeedToBeInSet(ITestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if its value is inside a well specified set
    """

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual in self.values

    def __str__(self):
        return "has to be in [{}]".format(', '.join(map(str, self.values)))


class TestContextMaskIgnore(ITestContextMaskOption):
    """
    A concrete option value is always compliant with this mask
    """

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return True

    def __str__(self):
        return "ignore"


class TestContextMaskNeedsNull(ITestContextMaskOption):
    """
    A concrete option value is compliant with this mask only if it is null
    """

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

    def is_compliant(self, i: int, actual: "Any", actual_set: List["ITestContext"]) -> bool:
        return actual is None

    def __str__(self):
        return "has to be null"
