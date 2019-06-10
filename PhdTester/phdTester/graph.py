import abc
import os
from typing import Any, Iterable, Tuple, List, Dict, Callable


class ISingleDirectedGraph(abc.ABC):

    @abc.abstractmethod
    def add_vertex(self, payload, aid: Any = None) -> Any:
        pass

    @abc.abstractmethod
    def get_vertex(self, aid) -> Any:
        pass

    @abc.abstractmethod
    def contains_vertex(self, aid) -> bool:
        pass

    @abc.abstractmethod
    def remove_vertex(self, aid) -> None:
        pass

    @abc.abstractmethod
    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        pass

    def __getitem__(self, item) -> Any:
        return self.get_vertex(item)

    def __setitem__(self, key, value) -> None:
        self.add_vertex(aid=key, payload=value)

    def __contains__(self, item) -> bool:
        return self.contains_vertex(item)

    @abc.abstractmethod
    def add_edge(self, source, sink, payload) -> None:
        pass

    @abc.abstractmethod
    def get_edge(self, source, sink) -> Any:
        pass

    @abc.abstractmethod
    def contains_edge(self, source, sink) -> bool:
        pass

    @abc.abstractmethod
    def remove_edge(self, source, sink) -> None:
        pass

    @abc.abstractmethod
    def edges(self, source: Any = None, sink: Any = None) -> Iterable[Tuple[Any, Any, Any]]:
        pass

    @abc.abstractmethod
    def successors(self, source: Any) -> Iterable[Any]:
        pass

    @abc.abstractmethod
    def predecessors(self, sink: Any) -> Iterable[Any]:
        pass

    @abc.abstractmethod
    def out_edges(self, source: Any) -> Iterable[Tuple[Any, Any, Any]]:
        """

        :param source: the key of the node whose out edges we want to compute
        :return: edges going out from source. it returns an iterable of 3 elements: the key of the source,
            the key of the sink and the payload attached to the edge
        """
        pass

    @abc.abstractmethod
    def in_edges(self, source: Any) -> Iterable[Tuple[Any, Any, Any]]:
        """

        :param source: the key of the node whose in edges we want to compute
        :return: edges going in source. it returns an iterable of 3 elements: the key of the source,
            the key of the sink and the payload attached to the edge
        """
        pass

    def in_degree(self, n: Any) -> int:
        """

        :param n: the key of the vertex
        :return: number of edges going in n
        """
        return len(list(self.in_edges(n)))

    def out_degree(self, n: Any) -> int:
        """

        :param n: the key of a vertex
        :return: number of edges going out from n
        """
        return len(list(self.out_edges(n)))

    @property
    def roots(self) -> Iterable[Tuple[Any, Any]]:
        """
        roots are vertices in the graph which have no predecessors
        :return: an iterable of tuples where the first element is the key of a root while the second one is the payload
            associated to the vertex
        """
        for n, payload in self.vertices():
            if self.in_degree(n) == 0:
                yield (n, payload)


class IMultiDirectedGraph(abc.ABC):

    @abc.abstractmethod
    def add_vertex(self, payload, aid: Any = None) -> Any:
        pass

    @abc.abstractmethod
    def get_vertex(self, aid) -> Any:
        pass

    @abc.abstractmethod
    def contains_vertex(self, aid) -> bool:
        pass

    @abc.abstractmethod
    def remove_vertex(self, aid) -> None:
        pass

    @abc.abstractmethod
    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        pass

    def __getitem__(self, item) -> Any:
        return self.get_vertex(item)

    def __setitem__(self, key, value) -> None:
        self.add_vertex(aid=key, payload=value)

    def __contains__(self, item) -> bool:
        return self.contains_vertex(item)

    @abc.abstractmethod
    def add_edge(self, source, sink, payload):
        """
        add a new edge in the graph. between the same source and sink there can be multiple albeit different edges
        :param source: the source of the edge
        :param sink: the sink of the edge
        :param payload: the payload attached to the given edge
        :return:
        """
        pass

    @abc.abstractmethod
    def get_edge(self, source, sink) -> Iterable[Tuple[Any, Any, Any]]:
        """
        get the edges between a source and a sink
        :param source:
        :param sink:
        :return:
        """
        pass

    @abc.abstractmethod
    def contains_edge(self, source, sink) -> bool:
        pass

    @abc.abstractmethod
    def remove_edge(self, source, sink, payload):
        pass

    @abc.abstractmethod
    def edges(self, source: Any = None, sink: Any = None) -> Iterable[Tuple[Any, Any, Any]]:
        pass

    @abc.abstractmethod
    def successors(self, source: Any) -> Iterable[Any]:
        """
        nodes which are connected to a direct edge whose source is `source`
        :param source:
        :return:
        """
        pass

    @abc.abstractmethod
    def predecessors(self, sink: Any) -> Iterable[Any]:
        """
        nodes which are connected with a direct edge whose sink is `sink`
        :param sink:
        :return:
        """
        pass

    @abc.abstractmethod
    def out_edges(self, source: Any) -> Iterable[Tuple[Any, Any, Any]]:
        """

        :param source: the key of the node whose out edges we want to compute
        :return: edges going out from source. it returns an iterable of 3 elements: the key of the source,
            the key of the sink and the payload attached to the edge
        """
        pass

    @abc.abstractmethod
    def in_edges(self, source: Any) -> Iterable[Tuple[Any, Any, Any]]:
        """

        :param source: the key of the node whose in edges we want to compute
        :return: edges going in source. it returns an iterable of 3 elements: the key of the source,
            the key of the sink and the payload attached to the edge
        """
        pass

    def in_degree(self, n: Any) -> int:
        """

        :param n: the key of the vertex
        :return: number of edges going in n
        """
        return len(list(self.in_edges(n)))

    def out_degree(self, n: Any) -> int:
        """

        :param n: the key of a vertex
        :return: number of edges going out from n
        """
        return len(list(self.out_edges(n)))

    @property
    def roots(self) -> Iterable[Tuple[Any, Any]]:
        """
        roots are vertices in the graph which have no predecessors
        :return: an iterable of tuples where the first element is the key of a root while the second one is the payload
            associated to the vertex
        """
        for n, payload in self.vertices():
            if self.in_degree(n) == 0:
                yield (n, payload)


class SimpleSingleDirectedGraph(ISingleDirectedGraph):

    next_id = 0

    def __init__(self):
        self._vertices = {}     # Dict[Any, Any]
        self._edges = {}        # Dict[Any, Dict[Any, Any]]

    @staticmethod
    def generate_vertex_id() -> int:
        result = SimpleSingleDirectedGraph.next_id
        SimpleSingleDirectedGraph.next_id += 1
        return result

    def check_vertex(self, vertex_name: str):
        # the node request may
        if vertex_name not in self._vertices:
            raise KeyError("node named '{}' not found. available names are {}".format(vertex_name, ', '.join(self._vertices.keys())))

    def add_vertex(self, payload, aid: Any = None) -> Any:
        if aid is None:
            aid = SimpleSingleDirectedGraph.generate_vertex_id()

        if aid in self._vertices:
            raise KeyError(f"key {aid} is already indexing a vertex!")

        self._vertices[aid] = payload
        return aid

    def get_vertex(self, aid) -> Any:
        if aid not in self._vertices:
            raise KeyError(f"key {aid} is not indexing a vertex in the graph!")

        return self._vertices[aid]

    def contains_vertex(self, aid: Any) -> bool:
        return aid in self._vertices

    def remove_vertex(self, aid) -> None:
        if aid not in self:
            raise KeyError(f"vertex {aid} not found!")
        # remove all the edges involved in the vertex
        edges_to_remove = []
        for s, t, payload in self.edges(source=aid, sink=None):
            edges_to_remove.append((s, t))
        for s, t, payload in self.edges(source=None, sink=aid):
            edges_to_remove.append((s, t))

        for s, t in edges_to_remove:
            self.remove_edge(s, t)

        del self._vertices[aid]

    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        return map(lambda k: (k, self._vertices[k]), self._vertices)

    def add_edge(self, source, sink, payload) -> None:
        if source not in self._edges:
            self._edges[source] = {}

        if sink in self._edges[source]:
            raise KeyError(f"edge {source}->{sink} already exists")

        self._edges[source][sink] = payload

    def get_edge(self, source, sink) -> Any:
        return self._edges[source][sink]

    def contains_edge(self, source, sink) -> bool:
        if source not in self._edges:
            return False

        if sink not in self._edges[source]:
            return False

        return True

    def remove_edge(self, source, sink) -> None:
        del self._edges[source][sink]

    def edges(self, source: Any = None, sink: Any = None) -> Iterable[Tuple[Any, Any, Any]]:
        sources = self._vertices.keys() if source is None else [source]
        sinks = self._vertices.keys() if sink is None else [sink]

        for source in sources:
            if source not in self._edges:
                continue
            for sink in self._edges[source]:
                if sink not in sinks:
                    continue
                yield (source, sink, self._edges[source][sink])

    def successors(self, n: Any) -> Iterable[Any]:
        self.check_vertex(n)
        # the vertex may have no successors. In this case we generate the stop iteration immediately
        if n not in self._edges:
            raise StopIteration()
        for sink, payload in self._edges[n].items():
            yield sink

    def predecessors(self, n: Any) -> Iterable[Any]:
        self.check_vertex(n)
        for source in self._edges:
            if n in self._edges[source]:
                yield source

    def out_edges(self, n: Any) -> Iterable[Tuple[Any, Any, Any]]:
        self.check_vertex(n)
        # the vertex may have no successors. In this case we generate the stop iteration immediately
        if n not in self._edges:
            raise StopIteration()
        for sink, payload in self._edges[n].items():
            yield (n, sink, payload)

    def in_edges(self, n: Any) -> Iterable[Tuple[Any, Any, Any]]:
        self.check_vertex(n)
        for source in self._edges:
            if n in self._edges[source]:
                yield (source, n, self._edges[source][n])


class SimpleMultiDirectedGraph(IMultiDirectedGraph):
    next_id = 0

    def __init__(self):
        self._vertices: Dict[Any, Any] = {}
        self._edges: Dict[Any, Dict[Any, List[Any]]] = {}

    @staticmethod
    def generate_vertex_id() -> int:
        result = SimpleMultiDirectedGraph.next_id
        SimpleMultiDirectedGraph.next_id += 1
        return result

    def check_vertex(self, vertex_name: str):
        # the node request may
        if vertex_name not in self._vertices:
            raise KeyError("node named '{}' not found. available names are {}".format(
                vertex_name,
                ', '.join(self._vertices.keys())
            ))

    def add_vertex(self, payload, aid: Any = None) -> Any:
        if aid is None:
            aid = SimpleMultiDirectedGraph.generate_vertex_id()

        if aid in self._vertices:
            raise KeyError(f"key {aid} is already indexing a vertex!")

        self._vertices[aid] = payload
        return aid

    def get_vertex(self, aid) -> Any:
        if aid not in self._vertices:
            raise KeyError(f"key {aid} is not indexing a vertex in the graph!")

        return self._vertices[aid]

    def contains_vertex(self, aid: Any) -> bool:
        return aid in self._vertices

    def remove_vertex(self, aid) -> None:
        if aid not in self:
            raise KeyError(f"vertex {aid} not found!")
        # remove all the edges involved in the vertex
        edges_to_remove = []
        for s, t, payload in self.edges(source=aid, sink=None):
            edges_to_remove.append((s, t, payload))
        for s, t, payload in self.edges(source=None, sink=aid):
            edges_to_remove.append((s, t, payload))

        for s, t, payload in edges_to_remove:
            self.remove_edge(s, t, payload)

        del self._vertices[aid]

    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        return map(lambda k: (k, self._vertices[k]), self._vertices)

    def add_edge(self, source, sink, payload):
        if source not in self._edges:
            self._edges[source] = {}

        if sink not in self._edges[source]:
            self._edges[source][sink] = []
        self._edges[source][sink].append(payload)

    def get_edge(self, source, sink) -> Iterable[Tuple[Any, Any, Any]]:
        for payload in self._edges[source][sink]:
            yield (source, sink, payload)

    def contains_edge(self, source, sink) -> bool:
        if source not in self._edges:
            return False

        if sink not in self._edges[source]:
            return False

        return True

    def remove_edge(self, source, sink, payload):
        if source not in self._edges:
            raise KeyError(f"source {source} has no outgoing edges!")
        if sink not in self._edges[source]:
            raise KeyError(f"source {source} has no outgoing edges towards {sink}!")
        self._edges[source][sink].remove(payload)
        if len(self._edges[source][sink]) == 0:
            del self._edges[source][sink]

    def edges(self, source: Any = None, sink: Any = None) -> Iterable[Tuple[Any, Any, Any]]:
        sources = self._vertices.keys() if source is None else [source]
        sinks = self._vertices.keys() if sink is None else [sink]

        for source in sources:
            if source not in self._edges:
                continue
            for sink in self._edges[source]:
                if sink not in sinks:
                    continue
                for payload in self._edges[source][sink]:
                    yield (source, sink, payload)

    def successors(self, n: Any) -> Iterable[Any]:
        self.check_vertex(n)
        # the vertex may have no successors. In this case we generate the stop iteration immediately
        if n not in self._edges:
            raise StopIteration()
        visited = set()
        for sink, payload in self._edges[n].items():
            if sink in visited:
                continue
            visited.add(sink)
            yield sink

    def predecessors(self, n: Any) -> Iterable[Any]:
        self.check_vertex(n)
        visited = set()
        for source in self._edges:
            if n in self._edges[source]:
                if source in visited:
                    continue
                visited.add(source)
                yield source

    def out_edges(self, n: Any) -> Iterable[Tuple[Any, Any, Any]]:
        self.check_vertex(n)
        # the vertex may have no successors. In this case we generate the stop iteration immediately
        if n not in self._edges:
            raise StopIteration()
        for sink, edges in self._edges[n].items():
            for payload in edges:
                yield (n, sink, payload)

    def in_edges(self, n: Any) -> Iterable[Tuple[Any, Any, Any]]:
        self.check_vertex(n)
        for source in self._edges:
            if n in self._edges[source]:
                for payload in self._edges[source][n]:
                    yield (source, n, payload)


class IMultiDirectedHyperGraph(abc.ABC):
    """
    A hyper graph. Each edge is actually an hyper edge with one source and several sinks. Each hyper edge
    has attacched a single payload.

    Between the same source and sinks we have have several hyperedges

    """

    class HyperEdge(object):
        """
        Represents an hyper edge inside an hyperedge graph.

        For example

        A -> (B, C, D)
        """
        def __init__(self, source: Any, sinks: Iterable[Any], payload: Any):
            """
            Create a new hyper edge
            :param source: the vertex representing the sourc eof the hyperedge
            :param sinks: sorted list of the sinks of the hyperedge
            :param payload: object attached to the hyperedge
            """
            self.source = source
            self.sinks = list(sinks)
            self.payload = payload

        def is_compliant(self, source: Any, sinks: Iterable[Any]) -> bool:
            """

            :param source:
            :param sinks:
            :return: true if the source and the sinks of 2 hyper edges are the same
            """
            return self.source == source and set(self.sinks) == set(sinks)

        def is_laid_on(self, vertices: Iterable[Any]) -> bool:
            """

            :param vertices: the set of vertices id to handle
            :return: if all the endpoints belong to the given set, false otherwise
            """
            return self.source in vertices and all(map(lambda sink: sink in vertices, self.sinks))

    @abc.abstractmethod
    def add_vertex(self, payload, aid: Any = None) -> Any:
        """
        Insert a new vertex in the hypergraph

        :param payload: the paylaod attached to the vertex
        :param aid: the id of the vertex
        :raises KeyError: if aid is already an id of a vertex in this graph. If None we will set an id
        :return: the id of the newly generated vrtex
        """
        pass

    @abc.abstractmethod
    def get_vertex(self, aid: Any) -> Any:
        """

        :param aid: the id of the vertex we're looking for
        :raises KeyError: if aid is not an id of a vertex in the graph
        :return: the payload of the vertex we're looking for
        """
        pass

    @abc.abstractmethod
    def contains_vertex(self, aid: Any) -> bool:
        """

        :param aid: the id of the vertex we're looking for
        :return: true if aid is an id of a vertex inside th graph, false otehrwise
        """
        pass

    @abc.abstractmethod
    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        """
        Iterable of all the vertices inside the graph
        :return:
        """
        pass

    @abc.abstractmethod
    def size(self) -> int:
        """

        :return: number of vertices in the graph
        """

        pass

    def is_empty(self) -> bool:
        """

        :return: true if the graph has no vertex, false otherwise
        """
        return self.size() == 0

    def get_vertices_number(self) -> int:
        return self.size()

    @abc.abstractmethod
    def add_edge(self, source: Any, sinks: Iterable[Any], payload) -> "IMultiDirectedHyperGraph.HyperEdge":
        """
        add a new hyper edge in the hyper graph. between the same source and sink there can be
        multiple albeit different edges
        :param source: the source of the edge
        :param sinks: a sorted list of sinks of the hyper edge
        :param payload: the payload attached to the given hyper edge
        :return: the hyperedge representing the edge we want
        """
        pass

    @abc.abstractmethod
    def get_edge(self, source: Any, sinks: Iterable[Any]) -> Iterable[HyperEdge]:
        """
        get the edges between a source and several hyperedge sinks
        :param source: the source of the hyperedge we want
        :param sinks: the sinks of the hyper edge we want
        :return: an iterable of all the hyper edges having source `source` and exactly the sinks in `sinks`
        """
        pass

    @abc.abstractmethod
    def contains_edge(self, source: Any, sinks: Iterable[Any]) -> bool:
        """
        Check if an hyper edge with such source and sinks exists in the graph
        :param source: the id of the source of the hyper graph
        :param sinks: the ids of the sinks of the hyper graph
        :return: true if there is at least one hyper edge with exactly the source and the sinks given, false otherwise
        """

        pass

    @abc.abstractmethod
    def successors(self, source: Any) -> Iterable[Any]:
        """
        vertices which are connected to a direct hyperedge whose source is `source`
        :param source: id of the node handle
        :return: iterable of all the vertices which are successors to the node `source`
        """
        pass

    @abc.abstractmethod
    def predecessors(self, sink: Any) -> Iterable[Any]:
        """
        vertices which are connected with a direct hyper edge whose at **least** one sink is `sink`
        :param sink: id of a sink
        :return: iterable of vertices which has at least one sink identical to `sink`
        """
        pass

    @abc.abstractmethod
    def edges(self) -> Iterable[HyperEdge]:
        """

        :return: iterable of all the hyper edges in the graph
        """
        pass

    @abc.abstractmethod
    def out_edges(self, source: Any) -> Iterable[HyperEdge]:
        """
        iterable of hyper edges going out from a vertex

        :param source: the key of the vertex whose out edges we want to compute
        :return: hyper edges going out from source.
        """
        pass

    @abc.abstractmethod
    def in_edges(self, source: Any) -> Iterable[HyperEdge]:
        """
        iterable of hyper edges going in a vertex

        :param source: the key of the node whose in edges we want to compute
        :return: edges going in source. it returns an iterable of 3 elements: the key of the source,
            the key of the sink and the payload attached to the edge
        """
        pass

    def in_degree(self, n: Any) -> int:
        """

        :param n: the key of the vertex
        :return: number of hyper edges going inside the vertex n
        """
        return len(list(self.in_edges(n)))

    def out_degree(self, n: Any) -> int:
        """

        :param n: the key of a vertex
        :return: number of hyper edges going out from n
        """
        return len(list(self.out_edges(n)))

    @property
    def roots(self) -> Iterable[Tuple[Any, Any]]:
        """
        roots are vertices in the graph which have no predecessors
        :return: an iterable of tuples where the first element is the key of a root while the second one is the payload
            associated to the vertex
        """
        for n, payload in self.vertices():
            if self.in_degree(n) == 0:
                yield (n, payload)


class DefaultMultiDirectedHyperGraph(IMultiDirectedHyperGraph):

    next_id = 0

    def __init__(self):
        self.__vertices: Dict[Any, Any] = {}
        self.__edges: List["IMultiDirectedHyperGraph.HyperEdge"] = []
        """
        List of hyper edges.
        """

    @staticmethod
    def _generate_vertex_id() -> int:
        """
        generates a new vertex id
        :return:
        """
        result = DefaultMultiDirectedHyperGraph.next_id
        DefaultMultiDirectedHyperGraph.next_id += 1
        return result

    def add_vertex(self, payload, aid: Any = None) -> Any:
        if aid is None:
            aid = DefaultMultiDirectedHyperGraph._generate_vertex_id()
        if aid in self.__vertices:
            raise KeyError(f"key {aid} is already an id of a vertex in this hypergraph!")
        self.__vertices[aid] = payload
        return aid

    def get_vertex(self, aid: Any) -> Any:
        return self.__vertices[aid]

    def contains_vertex(self, aid: Any) -> bool:
        return aid in self.__vertices

    def vertices(self) -> Iterable[Tuple[Any, Any]]:
        yield from self.__vertices.items()

    def size(self) -> int:
        return len(self.__vertices)

    def add_edge(self, source: Any, sinks: Iterable[Any], payload) -> "IMultiDirectedHyperGraph.HyperEdge":
        result = IMultiDirectedHyperGraph.HyperEdge(source=source, sinks=list(sinks), payload=payload)
        self.__edges.append(result)
        return result

    def get_edge(self, source: Any, sinks: Iterable[Any]) -> Iterable[IMultiDirectedHyperGraph.HyperEdge]:
        for edge in self.__edges:
            if edge.is_compliant(source, sinks):
                yield edge

    def contains_edge(self, source: Any, sinks: Iterable[Any]) -> bool:
        for edge in self.__edges:
            if edge.is_compliant(source, sinks):
                return True
        else:
            return False

    def successors(self, source: Any) -> Iterable[Any]:
        visited = set()
        for edge in self.__edges:
            if edge.source == source:
                for sink in edge.sinks:
                    if sink not in visited:
                        visited.add(sink)
                        yield sink

    def predecessors(self, sink: Any) -> Iterable[Any]:
        visited = set()
        for edge in self.__edges:
            if sink in edge.sinks and edge.source not in visited:
                visited.add(sink)
                yield edge.source

    def edges(self) -> Iterable[IMultiDirectedHyperGraph.HyperEdge]:
        yield from self.__edges

    def out_edges(self, source: Any) -> Iterable[IMultiDirectedHyperGraph.HyperEdge]:
        for edge in self.__edges:
            if edge.source == source:
                yield edge

    def in_edges(self, source: Any) -> Iterable[IMultiDirectedHyperGraph.HyperEdge]:
        for edge in self.__edges:
            if source in edge.sinks:
                yield edge

    def generate_image(self, output_file: str):
        with open(f"{output_file}.dot", "w") as dotfile:

            dotfile.write("digraph {\n")
            dotfile.write("\trankdir=\"TB\";\n")

            # add all edges
            for index, hyperedge in enumerate(self.__edges):
                dotfile.write(f"\tN{hyperedge.source} -> HE{index:04d} [arrowhead=\"none\"];\n")
                for sink in hyperedge.sinks:
                    dotfile.write(f"\tHE{index:04d} -> N{sink};\n")

            # add all vertices  of graph
            for index, vertex in self.__vertices.items():
                dotfile.write(f"\tN{index} [label=\"{index}\"];\n")

            # add all vertices of hyper edges
            for index, hyperedge in enumerate(self.__edges):
                dotfile.write(f"\tHE{index:04d} [shape=\"point\", label=\"\"];\n")

            dotfile.write("}\n")

        os.system(f"dot -Tsvg -o \"{output_file}.svg\" \"{output_file}.dot\"")
        os.remove(f"{output_file}.dot")

