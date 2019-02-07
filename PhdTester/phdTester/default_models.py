import abc
import logging
from typing import Iterable, List, Any

from phdTester.model_interfaces import ITestContextRepo, ITestContext, ITestContextMask, ITestContextRepoView, \
    IOptionDict, IUnderTesting, ITestingEnvironment, IStuffUnderTestMask, ITestEnvironmentMask, \
    ITestingGlobalSettings


class StandardOptionDict(IOptionDict):
    """
    Implementation of IOptionDict which directly queries all the public attributes of the object attached to it.

    Use only when:
     - the subtype has __dict__ attribute (if it's a class this is ensured by default)
     - the attributes you care about are public and are not properties (tagged with @proiperty)
     - it's not implemented as a tuple (so no __slots__ schenanigans)
    """

    def options(self) -> Iterable[str]:
        return (name for name in vars(self) if not name.startswith('_'))

    def get_option(self, name: str) -> Any:
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options")
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options")
        self.__dict__[name] = value


class AbstractTestingGlobalSettings(ITestingGlobalSettings, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingGlobalSettings.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractStuffUnderTest(IUnderTesting, StandardOptionDict, abc.ABC):

    def __init__(self):
        IUnderTesting.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestingEnvironment(ITestingEnvironment, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingEnvironment.__init__(self)
        StandardOptionDict.__init__(self)


class AbstractTestContext(ITestContext, abc.ABC):

    def __init__(self, ut: "IUnderTesting", te: "ITestingEnvironment"):
        ITestContext.__init__(self, ut=ut, te=te)


class AbstractStuffUnderTestMask(IStuffUnderTestMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        IStuffUnderTestMask.__init__(self)


class AbstractTestEnvironmentMask(ITestEnvironmentMask, StandardOptionDict, abc.ABC):

    def __init__(self):
        ITestingEnvironment.__init__(self)


class AbstractTestContextMask(ITestContextMask, abc.ABC):

    def __init__(self, ut: "IStuffUnderTestMask", te: "ITestEnvironmentMask"):
        ITestContextMask.__init__(self, ut=ut, te=te)


def _query_by_mask(m: "ITestContextMask", iterable: Iterable["ITestContext"]) -> Iterable["ITestContext"]:
    for tc in iterable:
        if m.is_complaint_with_test_context(tc, list(iterable)):
            yield tc


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

