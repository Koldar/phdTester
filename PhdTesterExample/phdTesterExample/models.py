from typing import Dict

import string_utils

import phdTester as phd


class SortTestContext(phd.AbstractTestContext):

    def __init__(self, ut: "SortAlgorithm" = None, te: "SortEnvironment" = None):
        super().__init__(ut, te)

    @property
    def ut(self) -> "SortAlgorithm":
        return self._ut

    @property
    def te(self) -> "SortEnvironment":
        return self._te


class SortAlgorithm(phd.AbstractStuffUnderTest):

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
        phd.AbstractStuffUnderTest.__init__(self)
        self.algorithm: str = None

    def get_label(self) -> str:
        return f"{self.algorithm}"


class SortEnvironment(phd.AbstractTestingEnvironment):

    def get_order_key(self) -> str:
        return "_".join(map(lambda o: f"{o}={str(self.get_option(o))}", self.options()))

    # @property
    # def key_alias(self) -> Dict[str, str]:
    #     return {
    #         "sequenceSize": "ss",
    #         "sequenceType": "st",
    #         "lowerBound": "lb",
    #         "upperBound": "ub",
    #         "run": "r",
    #     }
    #
    # @property
    # def value_alias(self) -> Dict[str, str]:
    #     return {}

    def __init__(self):
        phd.AbstractTestingEnvironment.__init__(self)
        self.sequenceSize: int = None
        self.sequenceType: str = None
        self.lowerBound: int = None
        self.upperBound: int = None
        self.run: int = None

    def get_label(self) -> str:
        return f"size={self.sequenceSize} type={self.sequenceType} lb={self.lowerBound} ub={self.upperBound} run={self.run}"


class SortSettings(phd.AbstractTestingGlobalSettings):

    def __init__(self):
        phd.AbstractTestingGlobalSettings.__init__(self)
        self.buildDirectory = None
        self.logLevel = None


class SortTestContextMask(phd.AbstractTestContextMask):

    def __init__(self, ut: "SortAlgorithmMask", te: "SortEnvironmentMask"):
        phd.AbstractTestContextMask.__init__(self, ut=ut, te=te)

    @property
    def ut(self) -> "SortAlgorithmMask":
        return self._ut

    @property
    def te(self) -> "SortEnvironmentMask":
        return self._te


class SortAlgorithmMask(phd.AbstractStuffUnderTestMask):

    def __init__(self):
        phd.AbstractStuffUnderTestMask.__init__(self)
        self.algorithm: "phd.ITestContextMaskOption" = None


class SortEnvironmentMask(phd.AbstractTestEnvironmentMask):

    def __init__(self):
        phd.AbstractTestEnvironmentMask.__init__(self)
        self.sequenceSize: phd.ITestContextMaskOption = None
        self.sequenceType: phd.ITestContextMaskOption = None
        self.lowerBound: phd.ITestContextMaskOption = None
        self.upperBound: phd.ITestContextMaskOption = None
        self.run: phd.ITestContextMaskOption = None


class PerformanceCsvRow(phd.AbstractCSVRow):

    def __init__(self):
        phd.AbstractCSVRow.__init__(self)
        self.run: int = None
        self.time: int = None
