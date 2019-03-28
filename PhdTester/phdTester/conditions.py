from typing import Callable, Any, List, Tuple

from phdTester.graph import IMultiDirectedGraph
from phdTester.model_interfaces import ITestContext, IDependencyCondition, IOptionNode


# class NeedsToBePresentCondition(IDependencyCondition):
#     """
#     Represents the fact that if the source condition is specified, then also the sink condition should be specified too
#     """
#
#     # TODO remove
#     # @property
#     # def kind(self) -> ConditionKind:
#     #     return ConditionKind.IS_PRESENT
#
#     def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return tc.contains_option(source_name) and tc.get_option(source_name) is not None
#
#     def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return tc.contains_option(sink_name) and tc.get_option(sink_name) is not None


class SatisfyMultiEdge(IDependencyCondition):
    """
    An edges which is a pseudo hyperedge. There is still a main source and sink, but there are other nodes which
    are involved in the decision of satisfying the constraint.
    """

    def __init__(self, condition: Callable[[IOptionNode, Any, IOptionNode, Any, List[Tuple[IOptionNode, Any]]], bool], third_party_nodes: List[str], allows_sink_visit: bool,
                 is_required: bool):
        IDependencyCondition.__init__(self)
        self._allowed_sink_visit = allows_sink_visit
        self._is_required = is_required
        self._condition = condition
        self.third_party_nodes = third_party_nodes

    def enable_sink_visit(self) -> bool:
        return self._allowed_sink_visit

    def is_required(self) -> bool:
        return self._is_required

    def accept(self, graph: IMultiDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return self._condition(
            graph.get_vertex(source_name), tc.get_option(source_name),
            graph.get_vertex(sink_name), tc.get_option(sink_name),
            [(graph.get_vertex(name), tc.get_option(name)) for name in self.third_party_nodes],
        )


class Satisfy(IDependencyCondition):

    def __init__(self, condition: Callable[[IOptionNode, Any, IOptionNode, Any], bool], allows_sink_visit: bool, is_required: bool):
        IDependencyCondition.__init__(self)
        self._allowed_sink_visit = allows_sink_visit
        self._is_required = is_required
        self._condition = condition

    def enable_sink_visit(self) -> bool:
        return self._allowed_sink_visit

    def is_required(self) -> bool:
        return self._is_required

    def accept(self, graph: IMultiDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
        return self._condition(
            graph.get_vertex(source_name), tc.get_option(source_name),
            graph.get_vertex(sink_name), tc.get_option(sink_name)
        )




# class NeedsToHaveValuesCondition(IDependencyCondition):
#     """
#     If the source `visit_condition` is satisfied then also the `condition` should be specified too
#     """
#
#     def __init__(self, condition: Callable[[IOptionNode, Any, IOptionNode, Any], bool], shoud_visit_condition: Callable[[IOptionNode, Any, IOptionNode, Any], bool]):
#         self.condition = condition
#         self.should_visit_condition = shoud_visit_condition
#
#     # TODO remove
#     # @property
#     # def kind(self) -> ConditionKind:
#     #     return ConditionKind.HAVE_VALUE
#
#     def should_visit(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return self.should_visit_condition(
#             graph.get_vertex(source_name), tc.get_option(source_name),
#             graph.get_vertex(sink_name), tc.get_option(sink_name)
#         )
#
#     def accept(self, graph: ISingleDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return self.condition(
#             graph.get_vertex(source_name), tc.get_option(source_name),
#             graph.get_vertex(sink_name), tc.get_option(sink_name)
#         )
