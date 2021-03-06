import abc
import io
import logging
import os
import shutil
from typing import Iterable, Tuple, Any, List, Dict

import pandas as pd

from phdTester import commons
from phdTester.common_types import KS001Str, PathStr, DataTypeStr
from phdTester.datasources.resource_managers import AbstractCsvResourceManager
from phdTester.exceptions import ResourceNotFoundError
from phdTester.model_interfaces import IDataSource, IResourceManager


class FileSystem(IDataSource):

    def __init__(self, root: str):
        IDataSource.__init__(self)
        self.root = os.path.abspath(root)

    def __enter__(self) -> "IDataSource":
        self.make_folders(self.root)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def name(self):
        return f"file system in {self.root}"

    def clear(self):
        shutil.rmtree(self.root)
        self.make_folders(self.root)

    def get_path(self, *p: str) -> str:
        """

        :param p: the path to fetch, relative to root
        :return: the absolute path of the resource pointed by p,
        """
        return os.path.abspath(os.path.join(self.root, *p))

    def make_folders(self, *p: str):
        """
        generate the set of folder in the path

        :param p: a comma separated list of directory to generate, relative to root
        :return:
        """

        folder = os.path.abspath(os.path.join(self.root, *p))
        logging.info(f"creating directory {folder}...")
        os.makedirs(folder,  exist_ok=True)


class AbstractFileSystemResourceManager(IResourceManager, abc.ABC):
    """
    A generic resource manager compliant only with FileSystem data source
    """

    def recursive_files_iterator(self, path: str, relative_to: str) -> Iterable[str]:
        for x in os.scandir(path):
            if x.is_file():
                yield os.path.relpath(os.path.join(path, x.name), start=relative_to)
            elif x.is_dir():
                yield from self.recursive_files_iterator(x.path, relative_to)
            # ignore other stuff

    def get_all(self, datasource: "IDataSource", path: str = None, data_type: str = None, colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> Iterable[Tuple[str, str, str]]:
        assert isinstance(datasource, FileSystem)
        abs_path = self._gen_absfile(datasource, path) if path is not None else datasource.root

        if os.path.exists(abs_path):
            # dirpath is the directory that we're currently exploring, relative to the root folder
            # dirname is the list of direct subdirectories in "dirpath"
            # filenames is the list files in "dirpath"

            for filename in self.recursive_files_iterator(abs_path, relative_to=abs_path):
                name = commons.get_ks001_basename_no_extension(filename, pipe=pipe)
                dt = commons.get_ks001_extension(filename, pipe=pipe)
                # dirpath is an absolute path
                # we need to convert it to "phdTester/tests"
                dirpath = os.path.relpath(path)

                if data_type is not None and dt == data_type:
                    yield (dirpath, name, dt)
                elif data_type is None:
                    yield (dirpath, name, dt)

    def contains(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> bool:
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        return os.path.exists(abs_filename)

    def remove(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str):
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        try:
            os.remove(abs_filename)
        except OSError:
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")

    def _gen_absfile(self, datasource: "FileSystem", *paths: str, basename: str = None, extension: str = None) -> str:
        result = os.path.join(datasource.root, *paths)
        if basename is not None:
            if extension is not None:
                basename = f"{basename}.{extension}"
            result = os.path.join(result, basename)
        return os.path.abspath(result)


class BinaryFileSystemResourceManager(AbstractFileSystemResourceManager):

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, FileSystem)

    def save_at(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str, content: Any):
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        os.makedirs(os.path.dirname(abs_filename), exist_ok=True)
        with open(abs_filename, "wb") as f:
            f.write(content)

    def get(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> bytes:
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        if not os.path.exists(abs_filename):
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")
        with open(abs_filename, "rb") as f:
            return f.read()

    def iterate_over(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Iterable[Any]:
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        if not os.path.exists(abs_filename):
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")
        with open(abs_filename, "rb") as f:
            for c in f:
                yield c


class ASCIIFileSystemResourceManager(AbstractFileSystemResourceManager):
    """
    A resource manager which reads an ASCII file and can iterate the file line by line
    """

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, FileSystem)

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def save_at(self, datasource: "FileSystem", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, content: Any):
        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension='csv')
        os.makedirs(os.path.dirname(abs_filename), exist_ok=True)
        with open(abs_filename, "w") as f:
            f.write(content)

    def get(self, datasource: "FileSystem", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Any:
        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        if not os.path.exists(abs_filename):
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")
        with open(abs_filename, "r") as f:
            return f.read()

    def iterate_over(self, datasource: "FileSystem", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Iterable[Any]:
        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension=data_type)
        if not os.path.exists(abs_filename):
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")
        with open(abs_filename, "r") as f:
            yield from f.readlines()


class CsvFileSystemResourceManager(AbstractFileSystemResourceManager, AbstractCsvResourceManager):

    def __init__(self):
        IResourceManager.__init__(self)

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, FileSystem)

    def save_at(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, content: Any):
        assert isinstance(datasource, FileSystem)
        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension='csv')
        os.makedirs(os.path.dirname(abs_filename), exist_ok=True)
        with open(abs_filename, "w") as f:
            f.write(content)

    def get(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Any:
        assert isinstance(datasource, FileSystem)

        abs_filename = self._gen_absfile(datasource, path, basename=ks001, extension='csv')
        if not os.path.exists(abs_filename):
            raise ResourceNotFoundError(f"resource {abs_filename} not found!")
        with open(abs_filename, "r") as f:
            return f.read()

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def head(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> \
            Dict[str, Any]:
        assert isinstance(datasource, FileSystem)

        raise NotImplementedError()
        # TODO implement
        # csv = io.StringIO(datasource.get(path, ks001, data_type))
        # last_line = pd.read_csv(csv).head(index)
        # last_line = commons.convert_pandas_csv_row_in_dict(last_line)
        # return last_line

    def tail(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> \
            Dict[str, Any]:
        assert isinstance(datasource, FileSystem)

        raise NotImplementedError()
        # TODO implement
        # csv = io.StringIO(datasource.get(path, ks001, data_type))
        # last_line = pd.read_csv(csv).tail(index)
        # last_line = commons.convert_pandas_csv_row_in_dict(last_line)
        # return last_line


