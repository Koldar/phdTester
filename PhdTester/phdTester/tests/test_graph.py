import unittest

from phdTester.graph import DefaultMultiDirectedHyperGraph


class MyTestCase(unittest.TestCase):

    def test_01(self):
        graph = DefaultMultiDirectedHyperGraph()

        graph.add_vertex("A")
        graph.add_vertex("B")
        graph.add_vertex("C")

        self.assertEqual(graph.size(), 3)
        self.assertEqual(graph.is_empty(), False)

    def test_02(self):
        graph = DefaultMultiDirectedHyperGraph()

        a = graph.add_vertex("A")
        b = graph.add_vertex("B")
        c = graph.add_vertex("C")

        graph.add_edge(a, [b, c], "a->bc")

        self.assertEqual(graph.out_degree(a), 1)
        self.assertEqual(graph.out_degree(b), 0)
        self.assertEqual(graph.out_degree(c), 0)
        self.assertEqual(graph.in_degree(a), 0)
        self.assertEqual(graph.in_degree(b), 1)
        self.assertEqual(graph.in_degree(c), 1)

        self.assertEqual(graph.get_edge(a, [b, c]), "a->bc")
        self.assertEqual(graph.get_edge(a, [c, b]), "a->bc")

    def test_03(self):
        graph = DefaultMultiDirectedHyperGraph()

        a = graph.add_vertex("A")
        b = graph.add_vertex("B")
        c = graph.add_vertex("C")
        d = graph.add_vertex("D")
        e = graph.add_vertex("E")
        f = graph.add_vertex("F")
        g = graph.add_vertex("G")

        graph.add_edge(a, [b, c], "a->bc")
        graph.add_edge(d, [b, c, e], "d->bce")
        graph.add_edge(e, [f, g], "e->fg")
        graph.add_edge(c, [e], "c->e")

        self.assertEqual(graph.size(), 7)
        self.assertEqual(graph.out_degree(a), 1)
        self.assertEqual(graph.out_degree(b), 0)
        self.assertEqual(graph.out_degree(c), 1)
        self.assertEqual(graph.out_degree(d), 1)
        self.assertEqual(graph.out_degree(e), 1)
        self.assertEqual(graph.out_degree(f), 0)
        self.assertEqual(graph.out_degree(g), 0)

        self.assertEqual(graph.in_degree(a), 0)
        self.assertEqual(graph.in_degree(b), 2)
        self.assertEqual(graph.in_degree(c), 2)
        self.assertEqual(graph.in_degree(d), 0)
        self.assertEqual(graph.in_degree(e), 2)
        self.assertEqual(graph.in_degree(f), 1)
        self.assertEqual(graph.in_degree(g), 1)

    def test_04(self):
        pass


if __name__ == '__main__':
    unittest.main()
