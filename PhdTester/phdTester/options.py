from typing import Any, List, Union

from phdTester import commons, option_types
from phdTester.model_interfaces import IOptionNode, OptionBelonging, OptionNodeKind, IOptionType


class FlagNode(IOptionNode):

    def __init__(self, long_name: str, ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             long_name=long_name,
                             option_type=option_types.Bool(),
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
    """
    An option node which can have one of finite number of possible values.

    It basically represents an enumeration
    """

    def __init__(self, long_name: str, values: List[str], ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             long_name=long_name,
                             option_type=option_types.Str(),
                             ahelp=ahelp,
                             belonging=belonging,
                             )
        self.values = values

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            type=self.option_type.to_argparse(),
                            required=False,
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


class SingleValueNode(IOptionNode):
    """
    An option in the option grapjh which can **always** have at most one actual value.

    An example are settings: here the option node can have 0 or 1 value.

    For example the log_level is a SingleValueNode since it can have one value in different
    test contexts.
    """

    def __init__(self, long_name: str, optional_type: IOptionType, ahelp: str, belonging: OptionBelonging, default_value: Any = None):
        IOptionNode.__init__(self,
                             long_name=long_name,
                             option_type=optional_type,
                             ahelp=ahelp,
                             belonging=belonging,
                             )
        self.__default_value = default_value

    def add_to_cli_option(self, parser: Any) -> None:

        # type generator
        if self.belonging in [OptionBelonging.ENVIRONMENT, OptionBelonging.UNDER_TEST]:
            # the user needs to put an evaluatable string
            t = str
        elif self.belonging in [OptionBelonging.SETTINGS]:
            t = self.option_type.to_argparse()
        else:
            raise ValueError(f"invalid belonging {self.belonging} or option {self.long_name}!")

        parser.add_argument(self.get_parser_name(),
                            type=t,
                            required=self.__default_value is None,
                            help=self.help,
                            default=self.__default_value,
                            )

    def convert_value(self, value: Any) -> Any:
        return self.option_type.convert(value)


class ValueNode(IOptionNode):
    """
    An option node which can have a value which can be a list of values (which can be inifinte, e.g., integers).

    For example in CombSort, the shrink factor is a ValueNode since it can have several different values in different
    test contexts
    """

    def __init__(self, long_name: str, optional_type: IOptionType, ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             long_name=long_name,
                             option_type=optional_type,
                             ahelp=ahelp,
                             belonging=belonging,
                             )

    def add_to_cli_option(self, parser: Any) -> None:

        # type generator
        if self.belonging in [OptionBelonging.ENVIRONMENT, OptionBelonging.UNDER_TEST]:
            # the user needs to put an evaluatable string
            t = str
        elif self.belonging in [OptionBelonging.SETTINGS]:
            t = self.option_type.to_argparse()
        else:
            raise ValueError(f"invalid belonging {self.belonging} or option {self.long_name}!")

        parser.add_argument(self.get_parser_name(),
                            type=t,
                            # since these nodes can have several possible values, their presence in the parser is always
                            # optional
                            required=False,
                            help=self.help,
                            )

    def convert_value(self, value: Any) -> Any:
        return self.option_type.convert(value)
