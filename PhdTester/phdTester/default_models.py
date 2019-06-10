import abc
import logging
from typing import Iterable, List, Any, Tuple, Dict

import numpy as np
import pandas as pd
import string_utils

from phdTester import commons
from phdTester.common_types import PathStr
from phdTester.model_interfaces import ITestContextRepo, ITestContext, ITestContextMask, ITestContextRepoView, \
    IOptionDict, IStuffUnderTest, ITestEnvironment, IStuffUnderTestMask, ITestEnvironmentMask, \
    IGlobalSettings, ICsvRow, IFunction2D, IDataWriter, IFunctionsDict, IDataContainerPathGenerator, ISubtitleGenerator
from phdTester.option_dicts import StandardOptionDict, DynamicOptionDict, DefaultAnonymuousOptionObject


class GnuplotDataWriter(IDataWriter):
    """
    Gnuplot sucks!
    """

    def __init__(self, filename: str, separator: str = " ", alias: str = "", carriage_return: str = "\n"):
        self.filename = filename
        self.alias = alias
        self.separator = separator
        self.carriage_return = carriage_return
        self._file = None

    def __enter__(self):
        self._file = open(self.filename, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def writeline(self, data: Iterable[Any]):
        if any(map(lambda x: isinstance(x, str), data)):
            return
        self._file.write(self.separator.join(map(lambda x: x.replace(self.separator, self.alias), map(lambda x: str(x), data))) + self.carriage_return)


class CsvDataWriter(IDataWriter):

    def __init__(self, filename: str, separator: str = ","):
        self.filename = filename
        self.separator = separator
        self._file = None

    def __enter__(self):
        self._file = open(self.filename, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def writeline(self, data: Iterable[Any]):
        self._file.write(self.separator.join(map(lambda x: x.replace(self.separator, ""), map(lambda x: str(x), data))) + "\n")


class DefaultSubtitleGenerator(ISubtitleGenerator):

    def fetch(self, tcm: "ITestContextMask") -> str:
        return tcm.te.get_have_value_string(ignore_some_tcm_keys=[])


class AbstractTestingGlobalSettings(IGlobalSettings, StandardOptionDict, abc.ABC):

    def __init__(self):
        IGlobalSettings.__init__(self)
        StandardOptionDict.__init__(self)


class DefaultGlobalSettings(IGlobalSettings, DynamicOptionDict):
    """
    A global settings implementation when the user do not want the help of the content assist

    This allows you to avoid generating the class containing the global settings yourself
    """
    def __init__(self):
        IGlobalSettings.__init__(self)
        DynamicOptionDict.__init__(self)


class AbstractStuffUnderTest(IStuffUnderTest, StandardOptionDict, abc.ABC):

    def __init__(self):
        IStuffUnderTest.__init__(self)
        StandardOptionDict.__init__(self)

    @property
    def key_alias(self) -> Dict[str, str]:
        return commons.generate_aliases(list(self.options()))

    @property
    def value_alias(self):
        return {}


class DefaultStuffUnderTest(IStuffUnderTest, DefaultAnonymuousOptionObject):
    """
    A stuff under test implementation when the user do not want the help of the content assist

    This allows you to avoid generating the class containing the stuff under test yourself
    """

    def __init__(self, fields: Iterable[str]):
        IStuffUnderTest.__init__(self)
        DefaultAnonymuousOptionObject.__init__(self, fields)

    @property
    def key_alias(self) -> Dict[str, str]:
        return commons.generate_aliases(list(self.options()))

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}


class AbstractTestingEnvironment(ITestEnvironment, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestEnvironment.__init__(self)
        StandardOptionDict.__init__(self)

    @property
    def key_alias(self) -> Dict[str, str]:
        return commons.generate_aliases(list(self.options()))

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}


class DefaultTestEnvironment(ITestEnvironment, DefaultAnonymuousOptionObject):
    """
    A global settings implementation when the user do not want the help of the content assist

    This allows you to avoid generating the class containing the global settings yourself
    """

    def __init__(self, fields: Iterable[str]):
        ITestEnvironment.__init__(self)
        DefaultAnonymuousOptionObject.__init__(self, fields)

    @property
    def key_alias(self) -> Dict[str, str]:
        return commons.generate_aliases(list(self.options()))

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}


class AbstractTestContext(ITestContext, abc.ABC):

    def __init__(self, ut: "IStuffUnderTest", te: "ITestEnvironment"):
        ITestContext.__init__(self, ut=ut, te=te)

    @property
    @abc.abstractmethod
    def ut(self) -> "IStuffUnderTest":
        """
        Return the stuff under test

        This abstract property exists because in this way IDE (like PyCharm) can detect an abstract method to implement.
        In this way the developer can remember to implement this property. Furthermore, this is an opportunity for
        the developer to specify the type of IStuffUnderTest for her purpose. In the context of sorting algorithm,
        The developer can implement the property as follows:

        ```
        @property
        def te(self) -> "SortAlgorithm":
            return self._ut
        ```

        The implementation is normally just `return self._ut`: the important piece here is the annotation of the return
        type; this allows IDE (e.g., PyCharm) to help the developer when coding the tests

        :return: the test enviroment
        """
        pass

    @property
    @abc.abstractmethod
    def te(self) -> "ITestEnvironment":
        """
        Return the test environment

        This abstract property exists because in this way IDE (like PyCharm) can detect an abstract method to implement.
        In this way the developer can remember to implement this property. Furthermore, this is an opportunity for
        the developer to specify the type of ITestEnviroment for her purpose. In the context of sorting algorithm,
        The developer can implement the property as follows:

        ```
        @property
        def te(self) -> "SortEnvironment":
            return self._te
        ```

        The implementation is normally just `return self._te`: the important piece here is the annotation of the return
        type; this allows IDE (e.g., PyCharm) to help the developer when coding the tests

        :return: the test enviroment
        """
        pass


class DefaultTestContext(ITestContext):

    def __init__(self, ut: IStuffUnderTest, te: ITestEnvironment):
        ITestContext.__init__(self, ut, te)


class AbstractStuffUnderTestMask(IStuffUnderTestMask, StandardOptionDict, abc.ABC):

    @abc.abstractmethod
    def __init__(self):
        IStuffUnderTestMask.__init__(self)


class DefaultStuffUnderTestMask(IStuffUnderTestMask, DefaultAnonymuousOptionObject):

    def __init__(self, fields: Iterable[str]):
        IStuffUnderTestMask.__init__(self)
        DefaultAnonymuousOptionObject.__init__(self, fields)


class AbstractTestEnvironmentMask(ITestEnvironmentMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestEnvironmentMask.__init__(self)


class DefaultTestEnvironmentMask(ITestEnvironmentMask, DefaultAnonymuousOptionObject):

    def __init__(self, fields: Iterable[str]):
        ITestEnvironmentMask.__init__(self)
        DefaultAnonymuousOptionObject.__init__(self, fields)


class AbstractTestContextMask(ITestContextMask, abc.ABC):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        ITestContextMask.__init__(self, ut=ut, te=te)


class DefaultTestContextMask(ITestContextMask):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        ITestContextMask.__init__(self, ut=ut, te=te)

    @property
    def ut(self) -> "IStuffUnderTestMask":
        return self._ut

    @property
    def te(self) -> "ITestEnvironmentMask":
        return self._te


def _query_by_mask(m: "ITestContextMask", iterable: Iterable["ITestContext"]) -> Iterable["ITestContext"]:
    for tc in iterable:
        if m.is_complaint_with_test_context(tc, list(iterable)):
            yield tc


class AbstractCSVRow(ICsvRow, StandardOptionDict, abc.ABC):
    """
    A csv row which natively implements all the IOptionDict methods by looking at  __dict__ public fields
    of the subtype
    """

    def __init__(self):
        ICsvRow.__init__(self)
        StandardOptionDict.__init__(self)


class SimpleTestContextRepoView(ITestContextRepoView):

    def __init__(self, values: Iterable[ITestContext], repo: "ITestContextRepo"):
        self.values = list(values)
        self._repo = repo

    def __iter__(self) -> Iterable[ITestContext]:
        return iter(self.values)

    def __getitem__(self, item: int) -> "ITestContext":
        return self.values[item]

    @property
    def repository(self) -> "ITestContextRepo":
        return self._repo

    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        return SimpleTestContextRepoView(list(_query_by_mask(m, self.values)), self._repo)

    def __len__(self) -> int:
        return len(self.values)


class SimpleTestContextRepo(ITestContextRepo):

    def __init__(self):
        ITestContextRepo.__init__(self)
        self.repo: List["ITestContext"] = []

    def append(self, v: "ITestContext"):
        self.repo.append(v)

    def __iter__(self) -> Iterable[ITestContext]:
        return iter(self.repo)

    def query_by_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        return SimpleTestContextRepoView(list(_query_by_mask(m, self.repo)), self)

    def query_by_finding_mask(self, m: "ITestContextMask") -> "ITestContextRepoView":
        """
        like query_by_mask but we autyomatically check if there is only one result and, if so, we return it
        :param m: the mask to apply
        :return:  the single element computed
        :raises ValueError: if the query returns 0 or more than 1 element
        """
        result = list(self.query_by_mask(m))
        if len(result) != 1:
            logging.critical("We obtained {} elements:\ntest context mask: {}\nelements:{}".format(len(result), str(m), "\n".join(map(str, result))))
            raise ValueError(f"we expected to have 1 element, not {len(result)}!")
        return result[0]

    def __len__(self) -> int:
        return len(self.repo)

    def clear(self):
        self.repo.clear()

