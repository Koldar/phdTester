import abc
from typing import Any, Iterable, Tuple, List, Dict


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
