import logging
from typing import Iterable, Any, Tuple, Union

from phdTester import IDataSource

import mysql.connector

from phdTester.common_types import KS001Str, DataTypeStr, PathStr
from phdTester.model_interfaces import IResourceManager


class MySqlDataSource(IDataSource):
    """
    A datasource which resides on a sql server

    In this datasource, each pair path - data type has it's own table, whose name is computed via
    _path_to_table_name.


    """

    def __init__(self, host_name: str, database_name: str, username: str, password: str):
        IDataSource.__init__(self)
        self.__host_name = host_name
        self.__database_name = database_name
        self.__username = username
        self.__password = password

        self.__connection = None

    def __enter__(self) -> "IDataSource":
        self.__connection = mysql.connector.connect(
            user=self.__username,
            password=self.__password,
            host=self.__host_name,
        )

        self.create_database(self.__database_name)
        self.use_database(self.__database_name)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__connection.close()

    @property
    def database_name(self) -> str:
        return self.__database_name

    def name(self):
        return f"MySQL {self.__username}@{self.__host_name} on db {self.__database_name}"

    def clear(self):
        self.drop_database(self.__database_name)
        self.create_database(self.__database_name)
        self.use_database(self.__database_name)

    def escape_text(self, text: Union[str, bytes]) -> Union[str, bytes]:
        if isinstance(text, str):
            return text.replace("'", "''")
        elif isinstance(text, bytes):
            return text.replace(b"'", b"''")
        else:
            raise TypeError(f"invlaid type of text {type(text)}!")

    def create_table(self, name: str, *fields: Tuple[str, type]):

        l = []
        for field_name, field_type in fields:
            if field_type == int:
                t = "INT NOT NULL"
            elif field_type == str:
                t = "TEXT NOT NULL"
            elif field_type == bool:
                t = "TINYINT NOT NULL"
            elif field_type == float:
                t = "FLOAT NOT NULL"
            elif field_type == Any:
                t = "BLOB NOT NULL"
            else:
                raise TypeError(f"invalid type {field_type}! Allowed are int, str, bool, float and Any")
            l.append(f"{field_name} {t}")

        self.run_instruction(f"""
            CREATE TABLE IF NOT EXISTS {name}(
                id INT AUTO_INCREMENT, PRIMARY KEY(id),
                {', '.join(l)}
            );
        """)

    def add_row_to_table(self, table_name: str, *values: Tuple[str, type, Any]):

        def convert(t: type, v: Any) -> Any:
            if t == int:
                return int(v)
            elif t == str:
                return f"'{str(v)}'"
            elif t == bool:
                return 1 if v is True else 0
            elif t == float:
                return float(v)
            else:
                raise TypeError(f"invalid type {t} of value {v}")

        columns_names = ', '.join(map(lambda x: x[0], values))
        columns_values = ', '.join(map(lambda x: convert(t=x[1], v=x[2]), values))
        self.run_instruction(f"""
            INSERT INTO `{table_name}`({columns_names}) VALUES ({columns_values});
        """)

    def get_rows_of_table(self, table_name: str) -> Iterable[Any]:
        yield from self.run_query(f"""
            SELECT * 
            FROM `{table_name}` 
        """)

    def get_row_such(self, table_name: str, field_name: str, field_value: str) -> Any:
        yield from self.run_query(f"""
            SELECT * 
            FROM `{table_name}`
            WHERE `{field_name}` = '{field_value}'
        """)

    def get_first_column_of_table(self, table_name: str, field_name: str, field_value: Any) -> Any:
        return self.fetch_first_of_query(f"""
            SELECT * 
            FROM `{table_name}`
            WHERE `{field_name}` = '{field_value}'
            LIMIT 1 
        """)

    def tables(self) -> Iterable[str]:
        yield from map(lambda x: x[0], self.run_query(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema ='{self.__database_name}';
        """))

    def has_table(self, name: str) -> bool:
        output, = self.fetch_first_of_query(f"""
            SELECT COUNT(*) AS table_exists
            FROM information_schema.tables
            WHERE table_schema = '{self.__database_name}' AND TABLE_NAME = '{name}'
        """)
        return output == 1

    def drop_table(self, name: str):
        self.run_instruction(f"""
            DROP TABLE IF EXISTS {name};
        """)

    def create_database(self, name: str):
        self.run_instruction(f"""
            CREATE DATABASE IF NOT EXISTS {name};
        """)

    def drop_database(self, name: str):
        self.run_instruction(f"""
            DROP DATABASE IF EXISTS {name};
        """)

    def use_database(self, name: str):
        self.run_instruction(f"""USE {name};""")

    def run_instruction(self, sql: str):
        """
        Run a sql which is not a query (e.g., create database, table, update row and so on)

        :param sql: the sql instruction to execute
        :return:
        """
        #FIXME https://pynative.com/python-mysql-blob-insert-retrieve-file-image-as-a-blob-in-mysql/
        cursor = self.__connection.cursor()
        logging.info(f"executing\n{sql}")
        cursor.execute(sql)
        # enable commit see https://stackoverflow.com/a/6027346/1887602
        self.__connection.commit()

    def run_query(self, sql: str) -> Iterable[Tuple[Any]]:
        """

        :param sql:
        :return: an iterable where each element represents a row generated by the query. Each row is encoded via
            a tuple. The lengtr hof the tuple depend on the SELECT clause
        """
        logging.info(f"executing\n{sql}")
        cursor = self.__connection.cursor()
        cursor.execute(sql)
        yield from cursor
        cursor.close()

    def fetch_first_of_query(self, sql: str) -> Any:
        logging.info(f"executing\n{sql}")
        for x in self.run_query(sql):
            return x


class MySqlBinaryResourceManager(IResourceManager):
    """
    A manager which saves in a sql datasource source which are binary values

    The structure is the same of MySqlASCIIResourceManager

    Each table row contains a single data container.
    Each table rerepsents a pair path-data type.
    Each table has 2 columns: the resource name and the resource content (both in text)
    """

    def __path_to_table_name(self, path: PathStr, data_type: DataTypeStr) -> str:
        return f"""{path.replace(r"/", r"$")}${data_type}"""

    def __table_name_to_path(self, table_name: str) -> Tuple[PathStr, DataTypeStr]:
        splits = table_name.split("$")
        return '/'.join(splits[:-1]), splits[-1]

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, MySqlDataSource)

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def save_at(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, content: Any):
        assert isinstance(datasource, MySqlDataSource)

        table_name = self.__path_to_table_name(path, data_type)

        datasource.run_instruction(f"""
            CREATE TABLE IF NOT EXISTS {table_name}(
                id INT AUTO_INCREMENT, PRIMARY KEY(id), 
                resourceName VARCHAR(5000) NOT NULL, 
                resourceContent LONGBLOB NOT NULL
            )
        """)

        ks001 = datasource.escape_text(ks001)
        content = datasource.escape_text(content)
        content = str(content)[2:-1]  # remove b' and ' from the head and tail respectively

        datasource.run_instruction(f"""
            INSERT INTO `{table_name}`(`resourceName`, `resourceContent`) VALUES ('{ks001}', '{content}')
        """)

    def get(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Any:
        assert isinstance(datasource, MySqlDataSource)

        index, resource_name, resource_content = datasource.get_first_column_of_table(
            table_name=f"{self.__path_to_table_name(path, data_type)}",
            field_name="resourceName",
            field_value=ks001,
        )

        return resource_content

    def get_all(self, datasource: "IDataSource", path: PathStr = None, data_type: DataTypeStr = None, colon: str = ':',
                pipe: str = '|', underscore: str = '_', equal: str = '=') -> Iterable[
        Tuple[PathStr, KS001Str, DataTypeStr]]:
        assert isinstance(datasource, MySqlDataSource)

        for table_name in datasource.tables():
            apath, adata_type = self.__table_name_to_path(table_name)
            if path is not None and path != apath:
                continue
            if data_type is not None and data_type != adata_type:
                continue
            for content_name, content_value in datasource.get_rows_of_table(table_name):
                yield (apath, content_name, adata_type)

    def contains(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> bool:
        assert isinstance(datasource, MySqlDataSource)

        index, resource_name, resource_content = datasource.get_first_column_of_table(
            table_name=f"{self.__path_to_table_name(path, data_type)}",
            field_name="resourceName",
            field_value=ks001,
        )

        return resource_content

    def remove(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr):
        assert isinstance(datasource, MySqlDataSource)

        datasource.run_instruction(f"""
            DELETE FROM {self.__path_to_table_name(path, data_type)}
            WHERE resourceName = '{ks001}'
        """)

    def iterate_over(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> \
    Iterable[Any]:
        content = self.get(
            datasource=datasource,
            path=path,
            ks001=ks001,
            data_type=data_type
        )
        for c in content:
            yield c


class MySqlASCIIResourceManager(IResourceManager):
    """
    A manager which saves in a sql datasource source which are simple humanc readable text

    Use this resource manager if you need to save something that is human readable, like a text.

    iterate_over semantic will yield one character of the text per call.


    Structure
    ---------

    Each table rerepsents a pair path-data type and has 2 columns: the resource name and
    the resource content (both in text).
    Each table row contains a single data container.
    """

    def __path_to_table_name(self, path: PathStr, data_type: DataTypeStr) -> str:
        return f"""{path.replace(r"/", r"$")}${data_type}"""

    def __table_name_to_path(self, table_name: str) -> Tuple[PathStr, DataTypeStr]:
        splits = table_name.split("$")
        return '/'.join(splits[:-1]), splits[-1]

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, MySqlDataSource)

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def save_at(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, content: Any):
        assert isinstance(datasource, MySqlDataSource)

        table_name = self.__path_to_table_name(path, data_type)
        if not datasource.has_table(table_name):
            datasource.create_table(
                f"{table_name}",
                ("resourceName", str),
                ("resourceContent", str),
            )

        datasource.add_row_to_table(
            f"{table_name}",
            ("resourceName", str, ks001),
            ("resourceContent", str, str(content))
        )

    def get(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Any:
        assert isinstance(datasource, MySqlDataSource)

        index, resource_name, resource_content = datasource.get_first_column_of_table(
            table_name=f"{self.__path_to_table_name(path, data_type)}",
            field_name="resourceName",
            field_value=ks001,
        )

        return resource_content

    def get_all(self, datasource: "IDataSource", path: PathStr = None, data_type: DataTypeStr = None, colon: str = ':',
                pipe: str = '|', underscore: str = '_', equal: str = '=') -> Iterable[Tuple[PathStr, KS001Str, DataTypeStr]]:
        assert isinstance(datasource, MySqlDataSource)

        for table_name in datasource.tables():
            apath, adata_type = self.__table_name_to_path(table_name)
            if path is not None and path != apath:
                continue
            if data_type is not None and data_type != adata_type:
                continue
            for content_id, content_name, content_value in datasource.get_rows_of_table(table_name):
                yield (apath, content_name, adata_type)

    def contains(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> bool:
        assert isinstance(datasource, MySqlDataSource)

        outcome = datasource.fetch_first_of_query(f"""
            SELECT COUNT(*) as total
            FROM `{self.__path_to_table_name(path, data_type)}`
            WHERE `resourceName` = `{ks001}`
        """)

        if outcome == 1:
            return True
        elif outcome == 0:
            return False
        else:
            raise ValueError(f"Multiple resources with name {ks001} in path={path}, datatype={data_type}!")

    def remove(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr):
        assert isinstance(datasource, MySqlDataSource)

        datasource.run_instruction(f"""
            DELETE FROM {self.__path_to_table_name(path, data_type)}
            WHERE `resourceName` = `{ks001}`
        """)

    def iterate_over(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr) -> Iterable[
        Any]:
        content = self.get(
            datasource=datasource,
            path=path,
            ks001=ks001,
            data_type=data_type
        )
        for c in content:
            yield c

