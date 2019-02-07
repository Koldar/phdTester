============
Introduction
============

During a Phd, it often arises the need to test *something* (e.g., an algorithm, a framework) over a *combination of parameters*. For instance, 
in the context of path planning, there are several algorithms, all of them with their wistles and tweaks, you can use to compute the shortest path
from a source to the target: you can use A* and several heuristics (like landmarks or euclidean distance), or you can use Dijkstra. The performance
of the algorithm under test may change over the *environment* where it is tested: for example an algorithm may perform better over a map and worse over
another one. Even worse, this environment may have its own parameters as well: for instance  environment may have different set of path planning queries
(simple, medium, difficult).

Therefore, you often need to test *some stuff* which has its own options over an environment which has its own options as well. Often, you need to
generate performances plot over all those combinations.

This problem can be solved by the PhdTester. It's a framework that let you generate all the combinations, plot the result and aggregate them in a
pdf report.