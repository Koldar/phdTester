from phdTester.common_types import PathStr
from phdTester.model_interfaces import IDataContainerPathGenerator, ITestContextMask


class CsvDataContainerPathGenerator(IDataContainerPathGenerator):

    def fetch(self, tcm: "ITestContextMask") -> PathStr:
        return "csvs"
