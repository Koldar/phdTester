
Introduction
============

During a Phd, it often arises the need to test *something* (e.g., an algorithm, a framework) over a 
*combination of parameters*. For instance, in the context of path planning, there are several algorithms, 
all of them with their wistles and tweaks, you can use to compute the shortest path
from a source to the target: you can use A* and several heuristics (like landmarks or euclidean distance), or you can use Dijkstra. The performance
of the algorithm under test may change over the *environment* where it is tested: 
for example an algorithm may perform better over a map and worse over another one. 
Even worse, this environment may have its own parameters as well: for instance  environment may have 
different set of path planning queries (simple, medium, difficult).

Therefore, you often need to test *some stuff* which has its own options over an environment which
 has its own options as well. Often, you need to generate performances plot over all those combinations.

This problem can be solved by the PhdTester. It's a framework that lets you:
 
1. generate all the test combinations;
2. plot the result;
3. and aggregate them in a pdf report.
 
Installation
============

Installation is very easy, just use:

```
pip install phd-tester
```

You may need to do this other step as well:

```
pip install dask[dataframe] --upgrade
```

Requirements
============

Phd Tester requires some additional tools in order to fully work. 
 - it needs `pdflatex` to generate the report. Hence, if you care about the report, 
 be sure to install it. For systems like Ubuntu, this can be effectively done via:

```
sudo apt-get install tex-live
```
 - It needs `dot` to generate a visual representation of the *optionGraph*. To be able to do this,
   execute the command:
   
```
sudo apt-get install graphviz
```

Concepts
========

n the following we will list important concepts that needs to be understood in order to use the framework:

Stuff under test
----------------

The "stuff under test" is the algorithm, procedure, model that you want to benchmark together with every 
configuration attached to it. For example if you want to test sorting algorithms, "stuffs under test" is 
the quicksort, bubblesort, mergesort, heapsort, randomsort. If a "stuff under test" has a parameter 
(for instance, heapsort implementation may require the maximum size of the underlying heap), such parameter 
is included in the "stuff under test". "Stuff under test" is treated in a special way when computing 
plots and csvs, so be sure to correctly identifying it;

Test Environment
----------------

The "test environment" are all the options which are not directly linked with your algorithm, but represents the context
where the algorithm is run in. For exmaple in the context of sorting algorithms, a test environment option
is the option representing the length of the sequence you want sort or the status the original sequence is:
 - random initialized;
 - already sorted;
 - reverse sorted;
 
Test Context
------------

The test context is a structure that uniquely identifies a single run of your algorithm. Thanks to the test context,
you can derive **all** the parameters identifying your test. This is by definition the union of "stuff under test"
options and "test environment" options.

KS001 Standard
--------------

TODO