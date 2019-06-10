import abc
from typing import List, Any, Callable, Tuple, Iterable, Set, Dict

from phdTester import conditions, option_types
from phdTester.conditions import IDependencyCondition
from phdTester.exceptions import UncompliantTestContextError
from phdTester.graph import SimpleMultiDirectedGraph, DefaultMultiDirectedHyperGraph, IMultiDirectedHyperGraph
from phdTester.model_interfaces import ITestContext, AbstractOptionNode, OptionBelonging, IOptionType, Priority, \
    ConditionOutcome
from phdTester.options import MultiValueNode, SingleFlagNode, MultiChoiceNode, SingleChoiceNode, SingleValueNode


class OptionGraph(DefaultMultiDirectedHyperGraph):
    """
    A graph which represents which allows us to understand if a test context represents a valid tests or not
    """

    def is_compliant_with_test_context(self, tc: "ITestContext", vertices_to_consider: Set[str], priority_to_ignore: Priority) -> bool:
        """
        Check if all the hyper edges which lays over `vertices_to_consider` have their constraint satisfied

        This function is not a DFS, but it just iterate over a list.

        :param tc: the test context whose compliance we need to check
        :param vertices_to_consider:
        :param priority_to_ignore:
        :return:
        """

        # we just iterate over all the hyper edges and we consider only the ones laid over the vertices to consider.
        # we ignore the hyperedges with high priority (since we assume they are true)

        for hyperedge in self.edges():
            source_name = hyperedge.source
            sinks = hyperedge.sinks
            condition = hyperedge.payload

            if not isinstance(condition, IDependencyCondition):
                raise TypeError(f"edge payload needs to be instance of IDependencyCondition!")
            if not hyperedge.is_laid_on(vertices_to_consider):
                continue
            if hyperedge.payload.priority() >= priority_to_ignore:
                continue

            valid = condition.accept(
                graph=self, tc=tc,
                source_name=source_name,
                source_option=self.get_vertex(source_name),
                source_value=tc.get_option(source_name),
                sinks=list(
                    map(lambda sink_name: (sink_name, self.get_vertex(sink_name), tc.get_option(sink_name)),
                        sinks))
            )

            if valid == ConditionOutcome.REJECT and condition.is_required():
                return False

        return True

    def fetches_options_to_consider(self, tc: "ITestContext", priority: Priority) -> Tuple[bool, Set[str]]:
        """
        Generates a set of option nodes ids which are the set of options relevant to the ITestContext.

        We assume that the only options which have greater priority than `priority` are those which, if followed,
        generate the set of relevant options for `tc`

        :param tc: the ITestContext under analysis
        :param priority: the priority of the relevant options
        :return: a tuple of 2 elements. The first is the success flag: if False the
            ITestContext is not compliant with even the most basic cosntraints; in this case the second
            value is semantically useless. If the flag is true, the second paramter is the set of relevant
            options for `tc`.
        """
        result = set()

        for vertex_name, vertex_value in self.roots:
            # this is not a complete DFS. We start only from the roots of the option graph and we analyze only
            # nodes reached from there.
            # roots should always be marked as "followed"
            result.add(vertex_name)
            try:
                self.__follow_hyperedges(
                    node_name=vertex_name,
                    hyperedge_filter=lambda hyperedge: hyperedge.payload.priority() >= priority,
                    visited=set(),
                    tc=tc,
                    followed=result
                )
            except UncompliantTestContextError:
                return False, set()
        return True, result

    def __follow_hyperedges(self, node_name: str, hyperedge_filter: Callable[[IMultiDirectedHyperGraph.HyperEdge], bool], visited: Set[str], tc: "ITestContext", followed: Set[str]):
        if node_name in visited:
            return
        visited.add(node_name)
        for hyperedge in self.out_edges(node_name):
            condition = hyperedge.payload
            source_name = hyperedge.source
            sinks = hyperedge.sinks

            if not isinstance(condition, IDependencyCondition):
                raise TypeError(f"edge payload needs to be instance of IDependencyCondition!")
            if not hyperedge_filter(hyperedge):
                # the edge is uncompliant. We ignore the hyperedge
                continue
            valid = condition.accept(
                graph=self, tc=tc,
                source_name=source_name,
                source_option=self.get_vertex(source_name),
                source_value=tc.get_option(source_name),
                sinks=list(
                    map(lambda sink_name: (sink_name, self.get_vertex(sink_name), tc.get_option(sink_name)),
                        sinks))
            )

            if valid == ConditionOutcome.REJECT and condition.is_required():
                # the condition is marked as "required". If it's invalid the combination is immediately marked as
                # "invalid".
                raise UncompliantTestContextError(f"condition {condition} failed")
            elif valid == ConditionOutcome.SUCCESS and condition.enable_sink_visit():
                # ok, the condition may or may not be required. If it allows the visit of the sinks,
                # we check if the condition is valid. If it's valid we recursively go in the sinks
                for sink in sinks:
                    self.__follow_hyperedges(
                        node_name=sink,
                        hyperedge_filter=hyperedge_filter,
                        visited=visited,
                        tc=tc,
                        followed=followed,
                    )
                    followed.add(sink)

            #there are other cases: if valid is NOT_RELEVANT we basically ignore the condition



    # def is_compliant_with(self, tc: "ITestContext", followed_vertices: Set[str]) -> bool:
    #     """
    #     Check if a test context is compliant with the option graph
    #
    #     To check if a test context is compliant with the option graph we use the following algorithm.
    #
    #     First of all we pickup the sources of the graph (i.e., vertices which aren't sinks). We then run a DFS on
    #     unvisited vertices.
    #
    #     if, during the DFS, a vertex hasalready been visited we avoid handling it.
    #     Otherwise we mark it as visited and we check all its outgoing conditions.
    #      - If a required condition is not satisfied the test context is deemed as "uncompliant";
    #      - If a condition which has "enable_sink_visit" set is encountered, we call the DFS on it; otherwise
    #        we continue.
    #
    #     We stop when we have processed all the sources of the option graph.
    #
    #     :param tc:
    #     :param followed_vertices:
    #     :return:
    #     """
    #
    #     visited = set()
    #     followed_vertices.clear()
    #
    #     def is_compliant_with_dfs(option_graph: "OptionGraph", node_name: str) -> bool:
    #         if node_name in visited:
    #             return True
    #         visited.add(node_name)
    #         for hyperedge in option_graph.out_edges(node_name):
    #             condition = hyperedge.payload
    #             source_name = hyperedge.source
    #             sinks = hyperedge.sinks
    #             if not isinstance(condition, IDependencyCondition):
    #                 raise TypeError(f"edge payload needs to be instance of IDependencyCondition!")
    #
    #             valid = condition.accept(
    #                 graph=self, tc=tc,
    #                 source_name=source_name,
    #                 source_option=option_graph.get_vertex(source_name),
    #                 source_value=tc.get_option(source_name),
    #                 sinks=list(map(lambda sink_name: (sink_name, option_graph.get_vertex(sink_name), tc.get_option(sink_name)), sinks))
    #             )
    #             if condition.is_required():
    #                 # the condition is marked as "required". If it's invalid the combination is immediately marked as
    #                 # "invalid".
    #                 if not valid:
    #                     return False
    #
    #             if condition.enable_sink_visit():
    #                 # ok, the condition may or may not be required. If it allows the visit of the sinks,
    #                 # we check if the condition is valid. If it's valid we recursively go in the sinks
    #                 if valid:
    #                     for sink in sinks:
    #                         if not is_compliant_with_dfs(option_graph, sink):
    #                             return False
    #                         followed_vertices.add(sink)
    #
    #         return True
    #
    #     for vertex_name, vertex_value in self.roots:
    #         # this is not a complete DFS. We start only from the roots of the option graph and we analyze only
    #         # nodes reached from there.
    #         # roots should always be marked as "followed"
    #         followed_vertices.add(vertex_name)
    #         if not is_compliant_with_dfs(self, vertex_name):
    #             return False
    #     return True

    def options(self) -> Iterable[Tuple[str, AbstractOptionNode]]:
        for name, v in self.vertices():
            if not isinstance(v, AbstractOptionNode):
                raise TypeError(f"overtex is not AbstractOptionNode!")
            yield (name, v)

    def generate_image(self, output_file: str):
        with open(f"{output_file}.dot", "w") as dotfile:

            dotfile.write("digraph {\n")
            dotfile.write("\trankdir=\"TB\";\n")

            # add all edges
            for index, hyperedge in enumerate(self.edges()):
                if hyperedge.payload.priority() == Priority.IMPORTANT:
                    color = "red"
                    width = 2
                elif hyperedge.payload.priority() == Priority.NORMAL:
                    color = "black"
                    width = 1
                else:
                    raise ValueError(f"invalid priority {hyperedge.payload.priority()}!")

                dotfile.write(f"\tN{hyperedge.source} -> HE{index:04d} [arrowhead=\"none\", width={width}, color=\"{color}\"];\n")
                for sink in hyperedge.sinks:
                    dotfile.write(f"\tHE{index:04d} -> N{sink} [width={width}, color=\"{color}\"];\n")

            # add all vertices  of graph
            for index, vertex in self.vertices():
                dotfile.write(f"\tN{index} [label=\"{index}\"];\n")

            # add all vertices of hyper edges
            for index, hyperedge in enumerate(self.edges()):
                dotfile.write(f"\tHE{index:04d} [shape=\"point\", label=\"\"];\n")

            dotfile.write("}\n")

        os.system(f"dot -Tsvg -o \"{output_file}.svg\" \"{output_file}.dot\"")
        #os.remove(f"{output_file}.dot")


class OptionBuilder(abc.ABC):

    def __init__(self):
        self.option_graph = OptionGraph()

    ####################################
    # FLAG
    ####################################

    def add_settings_flag(self, name: str, ahelp: str) -> "OptionBuilder":
        """
        Adds a flag corresponding to a boolean value.

        This flag will be used for a global setting in the tester
        :param name: name of the flag to add. e.g., if you write "foo", you will need to write "--foo" in CLI
        :param ahelp: description of what this flag is doing
        :return: the option builder
        """
        self.option_graph.add_vertex(aid=name, payload=SingleFlagNode(name, ahelp, OptionBelonging.SETTINGS))
        return self

    ####################################
    # CHOICE
    ####################################

    def add_under_testing_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing an "stuff under test" option which can have a discrete number
        of values. Values outside the ones used won't be allowed


        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param possible_values: the list of allowed values for the option
        :param ahelp: description of what these values do
        :return: the option builder
        """
        self.option_graph.add_vertex(
            aid=name,
            payload=MultiChoiceNode(name, possible_values, ahelp, OptionBelonging.UNDER_TEST)
        )
        return self

    def add_environment_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "test environment" option which can have a discrete number of
        values. Values outside the ones used won't be allowed

        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param possible_values: the list of allowed values for the option
        :param ahelp: derscription of what this option means
        :return: the option builder
        """
        self.option_graph.add_vertex(
            aid=name,
            payload=MultiChoiceNode(name, possible_values, ahelp, OptionBelonging.ENVIRONMENT)
        )
        return self

    def add_settings_multiplexer(self, name: str, possible_values: List[str], ahelp: str) -> "OptionBuilder":
        self.option_graph.add_vertex(
            aid=name,
            payload=SingleChoiceNode(name, possible_values, ahelp, OptionBelonging.SETTINGS)
        )
        return self

    ####################################
    # VALUE
    ####################################

    def _add_value(self, name: str, option_type: "IOptionType", ahelp: str, belonging: OptionBelonging, default: Any = None) -> "OptionBuilder":
        if not isinstance(option_type, IOptionType):
            raise TypeError(f"allowed values for \"option_type\" are only those inheriting from \"IOptionType\"! Got {type(option_type)}")
        self.option_graph.add_vertex(aid=name, payload=MultiValueNode(name, option_type, ahelp, belonging, default=default))
        return self

    def add_under_testing_value(self, name: str, option_type: "IOptionType", ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "stuff under test" option which can have infinite possible
        values. For example you can use it when you need to declare a integer option.


        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param option_type: the type of the option
        :param ahelp: description of the option
        :return: the option builder
        """
        if not isinstance(option_type, IOptionType):
            raise TypeError(f"allowed values for \"option_type\" are only those inheriting from \"IOptionType\"! Got {type(option_type)}")
        self.option_graph.add_vertex(
            aid=name,
            payload=MultiValueNode(name, option_type, ahelp, OptionBelonging.UNDER_TEST))
        return self

    def add_environment_value(self, name: str, option_type: "IOptionType", ahelp: str) -> "OptionBuilder":
        """
        Adds a node in the option graph representing a "test environment" option which can have infinite possible
        values. For example you can use it when you need to declare a integer option.

        :param name: name of the option. If you add "foo" you will need to write in CLI "--foo_values"
        :param option_type: the type of the option
        :param ahelp: description of the option
        :return: the option builder
        """
        if not isinstance(option_type, IOptionType):
            raise TypeError(f"allowed values for \"option_type\" are only those inheriting from \"IOptionType\"! Got {type(option_type)}")
        self.option_graph.add_vertex(
            aid=name,
            payload=MultiValueNode(name, option_type, ahelp, OptionBelonging.ENVIRONMENT))
        return self

    def add_settings_value(self, name: str, option_type: "IOptionType", ahelp: str, default: Any = None) -> "OptionBuilder":
        if not isinstance(option_type, IOptionType):
            raise TypeError(f"allowed values for \"option_type\" are only those inheriting from \"IOptionType\"! Got {type(option_type)}")
        self.option_graph.add_vertex(
            aid=name,
            payload=SingleValueNode(name, option_type, ahelp, OptionBelonging.SETTINGS, default_value=default))
        return self

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

    #################################################
    # CONDITIONS
    #################################################

    def option_value_needs_other_option(self, enabling_option: str, enabling_values: List[Any], enabled_option: str) -> "OptionBuilder":
        """
        if `option1` value is within the given set, then `option2` can't left set to None but it is required to
        be set as well. `None` cannot be inside `enabling_values`.
        If `option1` value is not in the given set, then everything is fine

        :param enabling_option: the option which can activate the option `enabled_option`
        :param enabling_values: the values which `enabling_option` needs to have in order to activate `enabled_option`
        :param enabled_option: the option which can be set if `option1_considered` has values in `option_1_values`
        :return:
        """
        if None in enabling_values:
            raise ValueError(f"None cannot be inside enabling_values!")

        # this condition has high priority since it is fundamental to detect which options are essential
        # for the test context
        self.option_graph.add_edge(enabling_option, [enabled_option], conditions.InSetImpliesNotNullSink(
            is_required=True,  # it's required because test contexts uncompliant with this are not real tests
            enable_sink_visit=True,
            allowed_values=enabling_values,
            priority=Priority.IMPORTANT,
        ))
        return self

    def option_can_be_used_only_when_other_satisfy(self, option1_name: str, option2_name: str,
                                                          condition: Callable[[Any, Any], bool]) -> "OptionBuilder":
        """
        Express the fact that there is a mandatory relationship between the 2 option values.

        In order for a test context to be compliant, the relationship must be ensured.
        The relationship is given by `condition`. This relationship is always relevant.

        :param option1_name: the first option
        :param option2_name: the second option
        :param condition: the relationship to be ensure
        :return:
        """

        self.option_graph.add_edge(option1_name, [option2_name], conditions.SimplePairCondition(
            is_required=True,
            enable_sink_visit=False,
            priority=Priority.NORMAL,
            condition=condition,
        ))

        return self

    def constraint_needs_to_happen(self, options_involved: List[str], condition: Callable[[List[Tuple[str, Any]]], bool]) -> "OptionBuilder":
        """
        Represents a contraint between several options which needs to be verified in order for the ITestContext
        to be compliant. The constraints won't be used to discover relevant options in the OptionGraph

        :param options_involved: list of options involved
        :param condition: condition that needs to happen if you want that a text context to be compliant
        :return: self
        """

        self.option_graph.add_edge(options_involved[0], options_involved[1:], conditions.NeedsToHappen(
            is_required=True,
            enable_sink_visit=False,
            priority=Priority.NORMAL,
            condition=condition,
        ))

        return self

    def constraint_cant_happen(self, options_involved: List[str], condition: Callable[[List[Tuple[str, Any]]], bool]):
        """
        Represents a contraint between several options which can't happen if you want the ITestContext
        to be compliant. The constraints won't be used to discover relevant options in the OptionGraph

        :param options_involved: list of options involved
        :param condition: condition that can't happen if you want that a text context to be compliant
        :return: self
        """

        self.option_graph.add_edge(options_involved[0], options_involved[1:], conditions.CantHappen(
            is_required=True,
            enable_sink_visit=False,
            priority=Priority.NORMAL,
            condition=condition,
        ))

        return self

    def prohibit_combination(self, options_involved: Dict[str, Any]) -> "OptionBuilder":
        """
        Remove a certain combination of values. If a test context has such combination of option vlaues,
        it's not compliant

        :param options_involved: a list where each cell is a pair: the first element is the option name while the
        second element is the option value associated. If a ITestContext has such combination of values, it won't be
        compliant
        :return: self
        """

        option_involved_list = list(options_involved.items())

        def condition(name_values: List[Tuple[str, Any]]) -> bool:
            for i, (name, value) in enumerate(name_values):
                if value != option_involved_list[i][1]:
                    return False
            return True

        self.option_graph.add_edge(option_involved_list[0][0], map(lambda x: x[0], option_involved_list[1:]),
                                   conditions.CantHappen(
                                       is_required=True,
                                       enable_sink_visit=False,
                                       priority=Priority.NORMAL,
                                       condition=condition,
                                   ))

        return self

    def ensure_combination(self, options_involved: Dict[str, Any]) -> "OptionBuilder":
        """
        Assert that a certain combination of values needs to **always** happen.
        If a test context do not have such combination of option values,
        it's not compliant

        :param options_involved: a list where each cell is a pair: the first element is the option name while the
        second element is the option value associated. If a ITestContext does not have such combination of values, it won't be
        compliant
        :return: self
        """

        option_involved_list = list(options_involved.items())

        def condition(name_values: List[Tuple[str, Any]]) -> bool:
            for i, (name, value) in enumerate(name_values):
                if value != option_involved_list[i][1]:
                    return False
            return True

        self.option_graph.add_edge(option_involved_list[0][0], map(lambda x: x[0], option_involved_list[1:]),
                                   conditions.NeedsToHappen(
                                       is_required=True,
                                       enable_sink_visit=False,
                                       priority=Priority.NORMAL,
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

        def condition(source: AbstractOptionNode, source_value: Any, sink: AbstractOptionNode, sink_value: Any):
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

        def cond(source: AbstractOptionNode, source_value: Any, sink: AbstractOptionNode, sink_value: Any, side_options: List[Tuple[AbstractOptionNode, Any]]) -> bool:
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

        def condition(option1: AbstractOptionNode, option1_value: Any, option2: AbstractOptionNode, option2_value: Any):
            return option1_value not in values1 and option2_value not in values2

        def condition2(source: AbstractOptionNode, source_value: Any, sink: AbstractOptionNode, sink_value: Any):
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

        # def condition(option1: AbstractOptionNode, option1_value: Any, option2: AbstractOptionNode, option2_value: Any):
        #     return option1_value not in option2
        #
        # def should_visit_condition(option1: AbstractOptionNode, option1_value: Any, option2: AbstractOptionNode, option2_value: Any):
        #     return True
        #
        # self.option_graph.add_edge(option1, options_prohibited, conditions.Satisfy(
        #
        # )(
        #     condition=condition,
        #     shoud_visit_condition=should_visit_condition
        # ))
        # return self


    def option_can_be_used_only_when_other_has_value(self, option_to_use: str, option_to_have_values: str,
                                                     values_to_have: List[Any]) -> "OptionBuilder":

        # def condition(option1: AbstractOptionNode, option1_value: Any, option2: AbstractOptionNode, option2_value: Any):
        #     return True
        #
        # def should_condition(option1: AbstractOptionNode, option1_value: Any, option2: AbstractOptionNode, option2_value: Any):
        #     return option2_value in values_to_have
        #
        # self.option_graph.add_edge(option_to_use, option_to_have_values,
        #                            NeedsToHaveValuesCondition(condition=condition, shoud_visit_condition=should_condition))
        # return self

        def condition(source: AbstractOptionNode, source_value: Any, sink: AbstractOptionNode, sink_value: Any):
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

        def condition(source: AbstractOptionNode, source_value: Any, sink: AbstractOptionNode, sink_value: Any):
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
