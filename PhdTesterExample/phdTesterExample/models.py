# TODO create __init__ which automatically import everything


# TODO make ut and te properties abstract: in this way the developer can override them
from typing import Dict

from phdTester import default_models
from phdTester.default_models import AbstractCSVRow, AbstractTestContextMask
from phdTester.model_interfaces import ITestContextMaskOption


class SortTestContext(default_models.AbstractTestContext):

    def __init__(self, ut: "SortAlgorithm" = None, te: "SortEnvironment" = None):
        super().__init__(ut, te)

    @property
    def ut(self) -> "SortAlgorithm":
        return self._ut

    @property
    def te(self) -> "SortEnvironment":
        return self._te


class SortAlgorithm(default_models.AbstractStuffUnderTest):

    @property
    def key_alias(self) -> Dict[str, str]:
        return {
            "algorithm": "a",
        }

    @property
    def value_alias(self) -> Dict[str, str]:
        # No alias
        return {}

    def __init__(self):
        self.algorithm: str = None

    # TODO create default implementation (like looking at the sorted sequence)
    def get_label(self) -> str:
        return f"{self.algorithm}"


class SortEnvironment(default_models.AbstractTestingEnvironment):

    def get_order_key(self) -> str:
        return "_".join(map(lambda o: f"{o}={str(self.get_option(o))}", self.options()))

    # TODO I should generate a mewthod which creates alias automatically (by looking at the camelCase
    @property
    def key_alias(self) -> Dict[str, str]:
        return {
            "sequenceSize": "ss",
            "sequenceType": "st",
            "lowerBound": "lb",
            "upperBound": "ub",
            "run": "r",
        }

    @property
    def value_alias(self) -> Dict[str, str]:
        return {}

    def __init__(self):
        default_models.AbstractTestingEnvironment.__init__(self)
        self.sequenceSize: int = None
        self.sequenceType: str = None
        self.lowerBound: int = None
        self.upperBound: int = None
        self.run: int = None

    # TODO create default implementation (like looking at the sorted sequence)
    def get_label(self) -> str:
        return f"size={self.sequenceSize} type={self.sequenceType} lb={self.lowerBound} ub={self.upperBound} run={self.run}"


class SortSettings(default_models.AbstractTestingGlobalSettings):

    def __init__(self):
        self.outputDirectory = None


# TODO this can be generated automatically. Make abstract the ut and te properties
class SortTestContextMask(AbstractTestContextMask):

    #TODO should be automatically set
    def __init__(self, ut: "SortAlgorithmMask", te: "SortEnvironmentMask"):
        AbstractTestContextMask.__init__(self, ut=ut, te=te)

    @property
    def ut(self) -> "SortAlgorithmMask":
        return self._ut

    @property
    def te(self) -> "SortEnvironmentMask":
        return self._te


class SortAlgorithmMask(default_models.AbstractStuffUnderTestMask):

    def __init__(self):
        self.algorithm: ITestContextMaskOption = None


class SortEnvironmentMask(default_models.AbstractTestEnvironmentMask):

    def __init__(self):
        self.sequenceSize: ITestContextMaskOption = None
        self.sequenceType: ITestContextMaskOption = None
        self.lowerBound: ITestContextMaskOption = None
        self.upperBound: ITestContextMaskOption = None
        self.run: ITestContextMaskOption = None


class PerformanceCsvRow(AbstractCSVRow):

    def __init__(self):
        AbstractCSVRow.__init__(self)
        self.run: int = None
        self.time: int = None
