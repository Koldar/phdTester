import abc
import enum
from typing import Callable, Any, List, Tuple, Iterable

from phdTester.graph import IMultiDirectedGraph, IMultiDirectedHyperGraph
from phdTester.model_interfaces import ITestContext, IDependencyCondition, AbstractOptionNode, Priority, \
    ConditionOutcome


# class SatisfyMultiEdge(IDependencyCondition):
#     """
#     An edges which is a pseudo hyperedge. There is still a main source and sink, but there are other nodes which
#     are involved in the decision of satisfying the constraint.
#     """
#
#     def __init__(self, condition: Callable[[AbstractOptionNode, Any, AbstractOptionNode, Any, List[Tuple[AbstractOptionNode, Any]]], bool], third_party_nodes: List[str], allows_sink_visit: bool,
#                  is_required: bool):
#         IDependencyCondition.__init__(self)
#         self._allowed_sink_visit = allows_sink_visit
#         self._is_required = is_required
#         self._condition = condition
#         self.third_party_nodes = third_party_nodes
#
#     def enable_sink_visit(self) -> bool:
#         return self._allowed_sink_visit
#
#     def is_required(self) -> bool:
#         return self._is_required
#
#     def accept(self, graph: IMultiDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return self._condition(
#             graph.get_vertex(source_name), tc.get_option(source_name),
#             graph.get_vertex(sink_name), tc.get_option(sink_name),
#             [(graph.get_vertex(name), tc.get_option(name)) for name in self.third_party_nodes],
#         )
#
#
# class Satisfy(IDependencyCondition):
#
#     def __init__(self, condition: Callable[[AbstractOptionNode, Any, AbstractOptionNode, Any], bool], allows_sink_visit: bool, is_required: bool):
#         IDependencyCondition.__init__(self)
#         self._allowed_sink_visit = allows_sink_visit
#         self._is_required = is_required
#         self._condition = condition
#
#     def enable_sink_visit(self) -> bool:
#         return self._allowed_sink_visit
#
#     def is_required(self) -> bool:
#         return self._is_required
#
#     def accept(self, graph: IMultiDirectedGraph, source_name: str, sink_name: str, tc: "ITestContext") -> bool:
#         return self._condition(
#             graph.get_vertex(source_name), tc.get_option(source_name),
#             graph.get_vertex(sink_name), tc.get_option(sink_name)
#         )


class AbstractDependencyCondition(IDependencyCondition, abc.ABC):

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority):
        self.__enable_sink_visit = enable_sink_visit
        self.__is_required = is_required
        self.__priority = priority

    def enable_sink_visit(self) -> bool:
        return self.__enable_sink_visit

    def is_required(self) -> bool:
        return self.__is_required

    def priority(self) -> Priority:
        return self.__priority


class SimplePairCondition(AbstractDependencyCondition):
    """
    A condition between 2 options. The condition is either SUCCESS or REJECT, hence it is always relevant.
    """

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority, condition: Callable[[Any, Any], bool]):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__condition = condition

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any,
               sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        if len(sinks) != 1:
            raise ValueError(f"for this condition we require that the hyperedge is infact a simple edge!")
        valid = self.__condition(source_value, sinks[0][2])
        return ConditionOutcome.SUCCESS if valid else ConditionOutcome.REJECT


class CantHappen(AbstractDependencyCondition):
    """
    Says that a test context is required to invalidate this condition in order to be compliant
    """

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority, condition: Callable[[List[Tuple[str, Any]]], bool]):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__condition = condition

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any,
               sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        values = [(source_name, source_value)]
        values.extend([(x[0], x[2]) for x in sinks])
        valid = self.__condition(values)
        return ConditionOutcome.REJECT if valid else ConditionOutcome.SUCCESS


class NeedsToHappen(AbstractDependencyCondition):
    """
    Says that a test context is required to satisfy this condition to be compliant
    """

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority, condition: Callable[[List[Tuple[str, Any]]], bool]):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__condition = condition

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any,
               sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        values = [(source_name, source_value)]
        values.extend([(x[0], x[2]) for x in sinks])
        valid = self.__condition(values)
        return ConditionOutcome.SUCCESS if valid else ConditionOutcome.REJECT


class NeedsToHappenWithContext(AbstractDependencyCondition):

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority,
                 condition: Callable[[List[Tuple[str, Any]], Any], bool], **condition_args):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__condition = condition
        self.__condition_args = condition_args

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any,
               sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        values = [(source_name, source_value)]
        values.extend([(x[0], x[2]) for x in sinks])
        valid = self.__condition(values, **self.__condition_args)
        return ConditionOutcome.SUCCESS if valid else ConditionOutcome.REJECT


class RequiresMapping(AbstractDependencyCondition):
    """
    The dependency is compliant when all endpoints of the hyperedge are not null and when the sink values are equal to
    the appliance of a given mapping to the source value.

    Example:

        --algorithm=MERGE
        --fullAlgorithm=MERGESORT, BUBBLESORT

    They are compliant only when algorithm + 'SORT' = fullAlgorithm

    """

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority, mapping: Callable[[Any], Any]):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__mapping = mapping

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any,
               sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        if source_value is None:
            return ConditionOutcome.REJECT
        for sink_name, sink_option, sink_value in sinks:
            if sink_value is None:
                return ConditionOutcome.REJECT
            if self.__mapping(source_value) != sink_value:
                return ConditionOutcome.REJECT


class InSetImpliesNotNullSink(AbstractDependencyCondition):
    """
    If the source value is inside a given set, then it is required that all sinks have not null values.

    The condition is always true if the souirce value is not inside the given set
    """

    def __init__(self, enable_sink_visit: bool, is_required: bool, priority: Priority, allowed_values: List[Any]):
        AbstractDependencyCondition.__init__(self, enable_sink_visit, is_required, priority)
        self.__allowed_values = allowed_values

    def accept(self, graph: "IMultiDirectedHyperGraph", tc: "ITestContext", source_name: str,
               source_option: "AbstractOptionNode", source_value: Any, sinks: List[Tuple[str, "AbstractOptionNode", Any]]) -> ConditionOutcome:
        if source_value in self.__allowed_values:
            for sink_name, sink_option, sink_value in sinks:
                if sink_value is None:
                    # a sink value in this condition is None, we cannot have it. The condition is uncompliant
                    return ConditionOutcome.REJECT
            else:
                return ConditionOutcome.SUCCESS
        else:
            # source is not in the allowed values, hence
            return ConditionOutcome.NOT_RELEVANT
