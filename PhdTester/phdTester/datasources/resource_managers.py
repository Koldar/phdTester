import abc
from typing import Dict, Iterable

from phdTester.common_types import KS001Str, PathStr, DataTypeStr
from phdTester.commons import UnknownStringCsvReader
from phdTester.model_interfaces import IResourceManager, IDataSource, ICsvResourceManager


class AbstractCsvResourceManager(ICsvResourceManager, abc.ABC):
    """
    Add behaviours to a generic resource manager which can handle csvs
    """

    def iterate_over(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Iterable[Dict[str, str]]:
        csv_content: str = self.get(datasource, path, ks001, data_type)
        with UnknownStringCsvReader(csv_content.splitlines()) as f:
            for row in f:
                yield row
