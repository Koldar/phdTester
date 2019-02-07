from typing import Callable, Any

from phdTester.graph import ISingleDirectedGraph
from phdTester.model_interfaces import ITestContext, IDependencyCondition, ConditionKind, IOptionNode


class NeedsToBePresentCondition(IDependencyCondition):
    """
    Represents the fact that if the source condition is specified, then also the sink condition should be specified too
    """

    @property
    def kind(self) -> ConditionKind:
        return ConditionKind.IS_PRESENT

    def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return tc.contains_option(source_name) and tc.get_option(source_name) is not None

    def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return tc.contains_option(sink_name) and tc.get_option(sink_name) is not None


class NeedsToHaveValuesCondition(IDependencyCondition):
    """
    If the source `visit_condition` is satisfied then also the `condition` should be specified too
    """

    def __init__(self, condition: Callable[[IOptionNode, Any, IOptionNode, Any], bool], shoud_visit_condition: Callable[[IOptionNode, Any, IOptionNode, Any], bool]):
        self.condition = condition
        self.should_visit_condition = shoud_visit_condition

    @property
    def kind(self) -> ConditionKind:
        return ConditionKind.HAVE_VALUE

    def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return self.should_visit_condition(
            graph.get_vertex(source_name), tc.get_option(source_name),
            graph.get_vertex(sink_name), tc.get_option(sink_name)
        )

    def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return self.condition(
            graph.get_vertex(source_name), tc.get_option(source_name),
            graph.get_vertex(sink_name), tc.get_option(sink_name)
        )
