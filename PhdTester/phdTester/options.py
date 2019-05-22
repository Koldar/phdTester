from typing import Any, List, Union

from phdTester import commons
from phdTester.model_interfaces import IOptionNode, OptionBelonging, OptionNodeKind, IOptionType


# TODO maybe create a seaprate module
class Int(IOptionType):
    pass


class Str(IOptionType):
    pass


class Float(IOptionType):
    pass


class Bool(IOptionType):
    pass


class PercentageInt(IOptionType, str):
    """
    A string which ends with a percentage symbol.

    Allowed values are "5", "5%" or "5.3%".
    The regex is:

    \d+|\d+%|\d+.\d+%
    """
    pass


class IntList(IOptionType, list):
    """
    A list of integers
    """
    pass


class BoolList(list):
    """
    A list of booleans
    """
    pass


class FloatList(IOptionType, list):
    """
    A list of floats
    """
    pass


class StrList(IOptionType, list):
    """
    A list of strings
    """
    pass


class PercentageIntList(IOptionType, list):
    """
    A list of evaluatable integers
    """
    pass


class FlagNode(IOptionNode):

    def __init__(self, long_name: str, ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             kind=OptionNodeKind.FLAG,
                             long_name=long_name,
                             option_type=bool,
                             ahelp=ahelp,
                             belonging=belonging,
                             )

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            action="store_true",
                            help=self.help,
                            )

    def convert_value(self, value: Any) -> Any:
        return bool(value)


class MultiPlexerNode(IOptionNode):

    def __init__(self, long_name: str, values: List[str], ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             kind=OptionNodeKind.MULTIPLEXER,
                             long_name=long_name,
                             option_type=str,
                             ahelp=ahelp,
                             belonging=belonging,
                             )
        self.values = values

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            type=self.option_type,
                            required=True,
                            help="""{}. Accepted values are {}""".format(
                                self.help,
                                "\n".join(map(lambda x: str(x), self.values))
                            ),
                            )

    def convert_value(self, value: Any) -> Any:
        if value not in self.values:
            raise ValueError("we have received {} but multiplexer deal only with {}".format(
                value,
                ', '.join(map(str, self.values))
            ))

        return str(value)


class ValueNode(IOptionNode):

    def __init__(self, long_name: str, optional_type: type, ahelp: str, belonging: OptionBelonging, default: Any = None):
        IOptionNode.__init__(self,
                             kind=OptionNodeKind.VALUE,
                             long_name=long_name,
                             option_type=optional_type,
                             ahelp=ahelp,
                             belonging=belonging,
                             )
        self.default_value = default

    def add_to_cli_option(self, parser: Any) -> None:

        # type generator
        if self.belonging in [OptionBelonging.ENVIRONMENT, OptionBelonging.UNDER_TEST]:
            # the user needs to put an evaluatable string
            t = str
        elif self.belonging in [OptionBelonging.SETTINGS]:
            if self.option_type in [Int, ]:
                t = int
            elif self.option_type in [Str, ]:
                t = str
            elif self.option_type in [Float, ]:
                t = float
            elif self.option_type in [Bool, ]:
                t = bool
            elif self.option_type in [PercentageInt]:
                t = str
            elif self.option_type in [IntList, BoolList, FloatList, StrList, PercentageIntList]:
                t = str
            else:
                raise TypeError(f"invalid type {self.option_type} of option {self.long_name}!")
        else:
            raise ValueError(f"invalid belonging {self.belonging} or option {self.long_name}!")

        parser.add_argument(self.get_parser_name(),
                            type=t,
                            required=self.default_value is None,
                            help=self.help,
                            default=self.default_value,
                            )

    def _parse_int(self, value: str) -> Union[str, int]:
        if isinstance(value, str):
            if commons.is_percentage(value):
                # e.g., "5%"
                return str(value)
            elif commons.is_number(value):
                # e.g., "5"
                return int(value)
            else:
                raise TypeError(f"PercentageInt (when str) can either be a percentage or an int!")
        elif isinstance(value, int):
            # e.g., 5
            return int(value)
        else:
            raise TypeError(f"PercentageInt can either be a str or an int")

    def convert_value(self, value: Any) -> Any:
        # simple types
        if self.option_type == Int:
            return int(value)
        elif self.option_type == Str:
            return str(value)
        elif self.option_type == Float:
            return float(value)
        elif self.option_type == Bool:
            return bool(value)
        # list types
        elif self.option_type in [StrList, IntList, FloatList, BoolList]:
            return commons.safe_eval(value)
        # percentage types
        elif self.option_type == PercentageInt:
            return self._parse_int(value)
        elif self.option_type in [PercentageIntList]:
            return list(map(lambda x: self._parse_int(x), commons.safe_eval(value)))
        else:
            raise TypeError(f"invalid option type {self.option_type} for option {self.long_name}!")
