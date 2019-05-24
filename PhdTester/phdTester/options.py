from typing import Any, List, Union

from phdTester import commons, option_types
from phdTester.model_interfaces import IOptionNode, OptionBelonging, OptionNodeKind, IOptionType


class FlagNode(IOptionNode):

    def __init__(self, long_name: str, ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             kind=OptionNodeKind.FLAG,
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

    def __init__(self, long_name: str, values: List[str], ahelp: str, belonging: OptionBelonging):
        IOptionNode.__init__(self,
                             kind=OptionNodeKind.MULTIPLEXER,
                             long_name=long_name,
                             option_type=option_types.Str(),
                             ahelp=ahelp,
                             belonging=belonging,
                             )
        self.values = values

    def add_to_cli_option(self, parser: Any) -> None:
        parser.add_argument(self.get_parser_name(),
                            type=self.option_type.to_argparse(),
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

    def __init__(self, long_name: str, optional_type: IOptionType, ahelp: str, belonging: OptionBelonging, default: Any = None):
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
            t = self.option_type.to_argparse()
        else:
            raise ValueError(f"invalid belonging {self.belonging} or option {self.long_name}!")

        parser.add_argument(self.get_parser_name(),
                            type=t,
                            required=self.default_value is None,
                            help=self.help,
                            default=self.default_value,
                            )

    def convert_value(self, value: Any) -> Any:
        return self.option_type.convert(value)
