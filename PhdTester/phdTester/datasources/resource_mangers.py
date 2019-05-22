import abc
from typing import Dict, Iterable

from phdTester.common_types import KS001Str
from phdTester.commons import UnknownStringCsvReader
from phdTester.model_interfaces import IResourceManager, IDataSource, ICsvResourceManager


class AbstractCsvResourceManager(ICsvResourceManager, abc.ABC):

    def can_handle_data_type(self, datasource: "IDataSource", data_type: str) -> bool:
        return data_type in ['csv']

    def iterate_over(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Iterable[Dict[str, str]]:
        csv_content: str = self.get(datasource, path, ks001, data_type)
        with UnknownStringCsvReader(csv_content.splitlines()) as f:
            for row in f:
                yield row