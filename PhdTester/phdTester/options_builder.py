import abc
from typing import List, Any, Callable, Tuple, Iterable, Set, Dict

from phdTester import conditions, option_types
from phdTester.conditions import IDependencyCondition
from phdTester.graph import SimpleMultiDirectedGraph
from phdTester.model_interfaces import ITestContext, IOptionNode, OptionBelonging, IOptionType
from phdTester.options import ValueNode, FlagNode, MultiPlexerNode


class OptionGraph(SimpleMultiDirectedGraph):

    def is_compliant_with(self, tc: "ITestContext", followed_vertices: Set[str]) -> bool:

        visited = set()
        followed_vertices.clear()

        def is_compliant_with_dfs(option_graph: "OptionGraph", node_name) -> bool:
            if node_name in visited:
                return True
            visited.add(node_name)
            for source, sink, condition in option_graph.out_edges(node_name):
                if not isinstance(condition, IDependencyCondition):
                    raise TypeError(f"edge payload needs to be instance of IDependencyCondition!")

                valid = condition.accept(self, source, sink, tc)
                if condition.is_required():
                    # the condition is marked as "required". If it's invalid the combination is immediately marked as
                    # "invalid".
                    if not valid:
                        return False

                if condition.enable_sink_visit():
                    # ok, the condition may or may not be required. If it allows the visit of the sinks,
                    # we check if the condition is valid. If it's valid we recursively go in the sinks
                    if valid:
                        if not is_compliant_with_dfs(option_graph, sink):
                            return False
                        followed_vertices.add(sink)


            return True

        for vertex_name, vertex_value in self.roots:
            # this is not a complete DFS. We start only from the roots of the option graph and we analyze only
            # nodes reached from there.
            # roots should always be marked as "followed"
            followed_vertices.add(vertex_name)
            if not is_compliant_with_dfs(self, vertex_name):
                return False
        return True

    def options(self) -> Iterable[Tuple[str, IOptionNode]]:
        for name, v in self.vertices():
            if not isinstance(v, IOptionNode):
                raise TypeError(f"overtex is not IOptionNode!")
            yield (name, v)


class OptionBuilder(abc.ABC):

    def __init__(self):
        self.option_graph = OptionGraph()

    def _add_flag(self, name: str, ahelp: str, belonging: OptionBelonging) -> "OptionBuilder":
        self.option_graph.add_vertex(aid=name, payload=FlagNode(name, ahelp, belonging))
        return self

    def add_settings_flag(self, name: str, ahelp: str) -> "OptionBuilder":
        """
        Adds a flag corresponding to a boolean value.

        This flag will be used for a global setting in the tester
        :param name: name of the flag to add. e.g., if you write "foo", you will need to write "--foo" in CLI
        :param ahelp: description of what this flag is doing
        :return: the option builder
        """
        return self._add_flag(name, ahelp, OptionBelonging.SETTINGS)

    def _add_multiplexer(self, name: str, possible_values: List[str], ahelp: str, belonging: OptionBelonging) -> "OptionBuilder":
        self.option_graph.add_vertex(aid=name, payload=MultiPlexerNode(name, possible_values, ahelp, belonging))
        return self

    def add_under_testing_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing an "stuff under test" option which can have a discrete number
        of values. Values outside the ones used won't be allowed


        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param possible_values: the list of allowed values for the option
        :param ahelp: description of what these values do
        :return: the option builder
        """
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.UNDER_TEST)

    def add_environment_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "test environment" option which can have a discrete number of
        values. Values outside the ones used won't be allowed

        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param possible_values: the list of allowed values for the option
        :param ahelp: derscription of what this option means
        :return: the option builder
        """
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.ENVIRONMENT)

    def add_settings_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.SETTINGS)

    def _add_value(self, name: str, option_type: "IOptionType", ahelp: str, belonging: OptionBelonging, default: Any = None) -> "OptionBuilder":
        if not isinstance(option_type, IOptionType):
            raise TypeError(f"allowed values for \"option_type\" are only those inheriting from \"IOptionType\"! Got {type(option_type)}")
        self.option_graph.add_vertex(aid=name, payload=ValueNode(name, option_type, ahelp, belonging, default=default))
        return self

    def add_under_testing_value(self, name: str, option_type: "IOptionType", ahelp: str, default: Any = None) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "stuff under test" option which can have infinite possible
        values. For example you can use it when you need to declare a integer option.


        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param option_type: the type of the option
        :param ahelp: description of the option
        :param default: if present, the option will have a default value. Otherwise it is considered as "required".
            Represent sthe default value the option will have if no value is passed through the CLI
        :return: the option builder
        """
        return self._add_value(name, option_type, ahelp, OptionBelonging.UNDER_TEST, default=default)

    def add_environment_value(self, name: str, option_type: "IOptionType", ahelp: str, default: Any = None) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "test environment" option which can have infinite possible
        values. For example you can use it when you need to declare a integer option.

        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param option_type: the type of the option
        :param ahelp: description of the option
        :param default: if present, the option will have a default value. Otherwise it is considered as "required".
            Represent sthe default value the option will have if no value is passed through the CLI
        :return: the option builder
        """
        return self._add_value(name, option_type, ahelp, OptionBelonging.ENVIRONMENT, default)

    def add_settings_value(self, name: str, option_type: "IOptionType", ahelp: str, default: Any = None) -> "OptionBuilder":
        return self._add_value(name, option_type, ahelp, OptionBelonging.SETTINGS, default)

    def add_default_settings(self, log_level: str = "logLevel", build_directory: str = "buildDirectory") -> "OptionBuilder":
        """
        Add a set of default settings which should most tester might need.

        The default settings that will be available to you with this function are the following:

         - `log_level`: configure the log level of the framework, accept one of the keywords available in
         `logging.basicConfig(level)`. Defaults to INFO
         - build_directory: configure the root of the filesystem where every file generated by the framework should
            be put. Default to `build`;

        :param log_level: the name of the option representing the log level
        :param build_directory: the name of the option representing the build_directory
        :return:
        """

        self.add_settings_value(
            name=log_level,
            option_type=option_types.Str(),
            default="INFO",
            ahelp="""
            the level of the log you want to have when runnning the tests. Allowed values are
            the ones available in basicConfig, namely: 
            DEBUG, INFO, WARN, CRITICAL
            """,
        )
        self.add_settings_value(
            name=build_directory,
            option_type=option_types.Str(),
            default="build",
            ahelp="""
            the directory where everything will be put from the tester 
            """,
        )

        return self

    # conditions

    def option_value_allows_other_option(self, option1_considered: str, option_1_values: List[Any], option2_enabled: str) -> "OptionBuilder":
        """
        if `option1` value is within the given set, then `option2` can't be set to None
        :param option1_considered: the option which can have the values `option_1_values`
        :param option_1_values: the values accepted
        :param option2_enabled: the option which can be set if `option1_considered` has values in `option_1_values`
        :return:
        """

        def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return option1_value in option_1_values

        self.option_graph.add_edge(option1_considered, option2_enabled, conditions.Satisfy(
            is_required=False,
            allows_sink_visit=True,
            condition=condition,
        ))

        return self

    def option_value_prohibits_other_option(self, option1: str, values: List[Any], options_prohibited: str) -> "OptionBuilder":
        """
        Some option values entirely excludes another option

        :param option1: the option which can have values `values`
        :param values: some possible values `option1` may have
        :param options_prohibited: the option which can't be set if `option1` has one value within `values`
        :return: option builder
        """

        def condition(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any):
            return source_value not in values

        self.option_graph.add_edge(option1, options_prohibited, conditions.Satisfy(
            is_required=True,
            allows_sink_visit=False,
            condition=condition,
        ))

        return self

    def option_values_mutually_exclusive_when(self, option1: str, values1: List[Any], option2: str, values2: List[Any], side_options_dict: Dict[str, Iterable[Any]]):
        """
        N options are mutually exclusive. When the N options have certain values, we fail the constraint

        If the option values are all within their respective sets, the constraint won't be satisfied

        :param option1: the first option
        :param values1: the possible values of the first option
        :param option2: the second option
        :param values2: the possible values of the second option
        :param side_options_dict: dictionary representing side options. Each key is an option name while each value is the set of values mutually exclusive
        :return: the graph builder
        """

        def cond(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any, side_options: List[Tuple[IOptionNode, Any]]) -> bool:
            if source_value not in values1:
                return True
            if sink_value not in values2:
                return True
            for o, v in side_options:
                if v not in side_options_dict[o.long_name]:
                    return True
            else:
                return False

        self.option_graph.add_edge(option1, option2, conditions.SatisfyMultiEdge(
            condition=cond,
            third_party_nodes=list(side_options_dict.keys()),
            allows_sink_visit=False,
            is_required=True,
        ))

        return self

    def option_values_mutually_exclusive(self, option1: str, values1: List[Any], option2: str, values2: List[Any]) -> "OptionBuilder":

        def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return option1_value not in values1 and option2_value not in values2

        def condition2(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any):
            return source_value not in values2 and sink_value not in values1

        self.option_graph.add_edge(option1, option2, conditions.Satisfy(
            is_required=True,
            allows_sink_visit=False,
            condition=condition
        ))
        self.option_graph.add_edge(option2, option1, conditions.Satisfy(
            is_required=True,
            allows_sink_visit=False,
            condition=condition2
        ))
        return self

        # def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     return option1_value not in option2
        #
        # def should_visit_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     return True
        #
        # self.option_graph.add_edge(option1, options_prohibited, conditions.Satisfy(
        #
        # )(
        #     condition=condition,
        #     shoud_visit_condition=should_visit_condition
        # ))
        # return self

    def option_can_be_used_only_when_other_string_satisfy(self, option_to_use: str, option_to_have_values: str,
                                                     condition: Callable[[str, str], bool]) -> "OptionBuilder":

        # def inner_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     assert isinstance(option1_value, str)
        #     assert isinstance(option2_value, str)
        #     return condition(option1_value, option2_value)
        #
        # def should_visit_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     return True
        #
        # self.option_graph.add_edge(option_to_use, option_to_have_values,
        #                            NeedsToHaveValuesCondition(
        #                                condition=inner_condition,
        #                                shoud_visit_condition=should_visit_condition
        #                            ))
        # return self

        def other_condition(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any):
            assert isinstance(source_value, str)
            assert isinstance(sink_value, str)
            return condition(source_value, sink_value)

        self.option_graph.add_edge(option_to_use, option_to_have_values, conditions.Satisfy(
            is_required=True,
            allows_sink_visit=True,
            condition=other_condition,
        ))

        return self

    def option_can_be_used_only_when_other_has_value(self, option_to_use: str, option_to_have_values: str,
                                                     values_to_have: List[Any]) -> "OptionBuilder":

        # def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     return True
        #
        # def should_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
        #     return option2_value in values_to_have
        #
        # self.option_graph.add_edge(option_to_use, option_to_have_values,
        #                            NeedsToHaveValuesCondition(condition=condition, shoud_visit_condition=should_condition))
        # return self

        def condition(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any):
            return sink_value in values_to_have

        self.option_graph.add_edge(option_to_use, option_to_have_values, conditions.Satisfy(
            is_required=False,
            allows_sink_visit=True,
            condition=condition,
        ))

        return self

    def option_can_be_used_only_when_other_is_present(self, option_to_use: str,
                                                      option_to_be_present: str) -> "OptionBuilder":
        # self.option_graph.add_edge(option_to_use, option_to_be_present, True)
        # return self

        def condition(source: IOptionNode, source_value: Any, sink: IOptionNode, sink_value: Any):
            return source_value is not None

        self.option_graph.add_edge(option_to_be_present, option_to_use, conditions.Satisfy(
            is_required=False,
            allows_sink_visit=True,
            condition=condition,
        ))

        return self

    def get_option_graph(self) -> OptionGraph:
        """

        :return: retrieve the instance of Option graph we have built so far.
        """
        return self.option_graph
