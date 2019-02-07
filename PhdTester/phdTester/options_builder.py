import abc
from typing import List, Any, Callable, Tuple, Iterable, Set

from phdTester.conditions import NeedsToHaveValuesCondition, IDependencyCondition
from phdTester.graph import SimpleSingleDirectedGraph
from phdTester.model_interfaces import ITestContext, IOptionNode, OptionBelonging
from phdTester.options import ValueNode, FlagNode, MultiPlexerNode


class OptionGraph(SimpleSingleDirectedGraph):

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

                if condition.should_visit(self, source, sink, tc):
                    if not condition.accept(self, source, sink, tc):
                        return False
                    if not is_compliant_with_dfs(option_graph, sink):
                        return False
                    followed_vertices.add(sink)

            return True

        for vertex_name, vertex_value in self.roots:
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

    def add_under_testing_flag(self, name: str, ahelp: str) -> "OptionBuilder":
        return self._add_flag(name, ahelp, OptionBelonging.UNDER_TEST)

    def add_environment_flag(self, name: str, ahelp: str) -> "OptionBuilder":
        return self._add_flag(name, ahelp, OptionBelonging.ENVIRONMENT)

    def add_settings_flag(self, name: str, ahelp: str) -> "OptionBuilder":
        return self._add_flag(name, ahelp, OptionBelonging.SETTINGS)

    def _add_multiplexer(self, name: str, possible_values: List[str], ahelp: str,
                        belonging: OptionBelonging) -> "OptionBuilder":
        self.option_graph.add_vertex(aid=name, payload=MultiPlexerNode(name, possible_values, ahelp, belonging))
        return self

    def add_under_testing_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.UNDER_TEST)

    def add_environment_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.ENVIRONMENT)

    def add_settings_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        return self._add_multiplexer(name, possible_values, ahelp, OptionBelonging.SETTINGS)

    def _add_value(self, name: str, option_type: type, ahelp: str, belonging: OptionBelonging, default: Any = None) -> "OptionBuilder":
        self.option_graph.add_vertex(aid=name, payload=ValueNode(name, option_type, ahelp, belonging, default=default))
        return self

    def add_under_testing_value(self, name: str, option_type: type, ahelp: str, default: Any = None) -> "OptionBuilder":
        return self._add_value(name, option_type, ahelp, OptionBelonging.UNDER_TEST, default=default)

    def add_environment_value(self, name: str, option_type: type, ahelp: str, default: Any = None) -> "OptionBuilder":
        return self._add_value(name, option_type, ahelp, OptionBelonging.ENVIRONMENT, default)

    def add_settings_value(self, name: str, option_type: type, ahelp: str, default: Any = None) -> "OptionBuilder":
        return self._add_value(name, option_type, ahelp, OptionBelonging.SETTINGS, default)

    # conditions

    def option_value_allows_other_option(self, option1_considered: str, option_1_values: List[Any], option2_enabled: str) -> "OptionBuilder":

        def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return True

        def should_visit_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return option1_value in option_1_values

        self.option_graph.add_edge(option1_considered, option2_enabled, NeedsToHaveValuesCondition(
            condition=condition,
            shoud_visit_condition=should_visit_condition
        ))

        return self

    def option_can_be_used_only_when_other_string_satisfy(self, option_to_use: str, option_to_have_values: str,
                                                     condition: Callable[[str, str], bool]) -> "OptionBuilder":

        def inner_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            assert isinstance(option1_value, str)
            assert isinstance(option2_value, str)
            return condition(option1_value, option2_value)

        def should_visit_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return True

        self.option_graph.add_edge(option_to_use, option_to_have_values,
                                   NeedsToHaveValuesCondition(
                                       condition=inner_condition,
                                       shoud_visit_condition=should_visit_condition
                                   ))
        return self

    def option_can_be_used_only_when_other_has_value(self, option_to_use: str, option_to_have_values: str,
                                                     values_to_have: List[Any]) -> "OptionBuilder":

        def condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return True

        def should_condition(option1: IOptionNode, option1_value: Any, option2: IOptionNode, option2_value: Any):
            return option2_value in values_to_have

        self.option_graph.add_edge(option_to_use, option_to_have_values,
                                   NeedsToHaveValuesCondition(condition=condition, shoud_visit_condition=should_condition))
        return self

    def option_can_be_used_only_when_other_is_present(self, option_to_use: str,
                                                      option_to_be_present: str) -> "OptionBuilder":
        self.option_graph.add_edge(option_to_use, option_to_be_present, True)
        return self

    def get_option_graph(self) -> OptionGraph:
        return self.option_graph
