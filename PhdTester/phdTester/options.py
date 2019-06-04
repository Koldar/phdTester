from typing import Any, List, Union

from phdTester import commons, option_types
from phdTester.model_interfaces import AbstractOptionNode, OptionBelonging, IOptionType


class SingleFlagNode(AbstractOptionNode):
    """
    An option node which is a flag (namely in CLI it is either "--flag" or totally absent

    This flag is "single" since during different runs of test contexts, it always has the same value
    """

    def __init__(self, long_name: str, ahelp: str, belonging: OptionBelonging):
        AbstractOptionNode.__init__(self,
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
        return self.option_type.convert(value)


class MultiFlagNode(AbstractOptionNode):
    """
    An option node which is a flag (namely in CLI it is either "--flag" or totally absent

    It's multi in the sense that during different test contexts, it can have different values
    """

    def __init__(self, long_name: str, ahelp: str, belonging: OptionBelonging):
        AbstractOptionNode.__init__(self,
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
        return self.option_type.convert(value)


class SingleChoiceNode(AbstractOptionNode):
    """
    An option node which can have one of finite number of possible values.

    It basically represents an enumeration.
    It's "single" in the sense that during different runs of test contexts, it always has the same value
    """
    def __init__(self, long_name: str, values: List[str], ahelp: str, belonging: OptionBelonging, default_value: Any = None):
        AbstractOptionNode.__init__(self,
                                    long_name=long_name,
                                    option_type=option_types.Str(),
                                    ahelp=ahelp,
                                    belonging=belonging,
                                    )
        self.values = values
        self.__default_value = default_value

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            type=self.option_type.to_argparse(),
                            required=self.__default_value is None,
                            default=self.__default_value,
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


class MultiChoiceNode(AbstractOptionNode):
    """
    An option node which can have one of finite number of possible values.

    It basically represents an enumeration.

    It's multi in the sense that during different test contexts, it can have different values
    """

    def __init__(self, long_name: str, values: List[str], ahelp: str, belonging: OptionBelonging):
        AbstractOptionNode.__init__(self,
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


class SingleValueNode(AbstractOptionNode):
    """
    An option in the option grapjh which can **always** have at most one actual value.

    An example are settings: here the option node can have 0 or 1 value.

    For example the log_level is a SingleValueNode since it can have one value in different
    test contexts.
    """

    def __init__(self, long_name: str, optional_type: IOptionType, ahelp: str, belonging: OptionBelonging, default_value: Any = None):
        AbstractOptionNode.__init__(self,
                                    long_name=long_name,
                                    option_type=optional_type,
                                    ahelp=ahelp,
                                    belonging=belonging,
                                    )
        self.__default_value = default_value

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            type=self.option_type.to_argparse(),
                            required=self.__default_value is None,
                            help=self.help,
                            default=self.__default_value,
                            )

    def convert_value(self, value: Any) -> Any:
        return self.option_type.convert(value)


class MultiValueNode(AbstractOptionNode):
    """
    An option node which can have a value which can be a list of values (which can be infinte, e.g., integers).

    For example in CombSort, the shrink factor is a MultiValueNode since it can have several different values in different
    test contexts
    """

    def __init__(self, long_name: str, optional_type: IOptionType, ahelp: str, belonging: OptionBelonging):
        AbstractOptionNode.__init__(self,
                                    long_name=long_name,
                                    option_type=optional_type,
                                    ahelp=ahelp,
                                    belonging=belonging,
                                    )

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            # since it can have several values in test contexts, the content is a string
                            type=str,
                            # since these nodes can have several possible values, their presence in the parser is always
                            # optional
                            required=False,
                            help=self.help,
                            )

    def convert_value(self, value: Any) -> Any:
        return self.option_type.convert(value)
