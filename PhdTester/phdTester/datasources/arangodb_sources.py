import abc
import csv
import logging
from typing import Any, Tuple, Iterable, Dict, List

from arango import ArangoClient
from arango.collection import Collection, StandardCollection
from arango.database import Database

from phdTester import commons
from phdTester.common_types import KS001Str, PathStr, DataTypeStr
from phdTester.datasources.resource_managers import AbstractCsvResourceManager
from phdTester.exceptions import ResourceNotFoundError
from phdTester.model_interfaces import IDataSource, IResourceManager


class ArangoDB(IDataSource):
    """
    A datasource where every testing data is stored within an ArangoDB

    Inside this datasource, each raw data is actually a arango collection.
    """

    KS001_TO_COLLECTIONID_NAME = "ks001-to-collectionid"

    def __init__(self, host: str, port: int, username: str, password: str, database_name: str):
        IDataSource.__init__(self)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database_name = database_name
        """
        Name of the database to consider
        """
        self.client: ArangoClient = None
        self.database: Database = None
        """
        Instance of the database to edit
        """
        self.ks001_to_collection: StandardCollection = None
        """
        Collection containing the mapping between KS001 names and ids
        """
        self.sys_db: Database = None

    def name(self):
        return f"ArangoDB with python-arango {self.username}@{self.host}:{self.port}"

    def clear(self):
        for collection_name in self.get_all_collection_names():
            if collection_name.startswith('_'):
                continue
            logging.info(f"dropping collection {collection_name}")
            self.remove_collection(self.database, collection_name)

    def __enter__(self) -> "IDataSource":
        # create connection to arango
        logging.info(f"host={self.host} port={self.port} username={self.username} database={self.database_name}")
        self.client = ArangoClient(protocol='http', host=self.host, port=self.port)
        self.sys_db = self.client.db('_system', username=self.username, password=self.password)

        # create or open a database
        self.database = self.fetch_or_create_database(self.database_name)

        # let the user have the permission over the database
        self.let_user_access_database(username=self.username, db_name=self.database_name)

        # create the default ks001 to collection id collection if not existing
        self.ks001_to_collection = self.fetch_or_create_collection(ArangoDB.KS001_TO_COLLECTIONID_NAME)
        self.add_hash_index_on_field(self.ks001_to_collection, fields=["ks001", "index"], unique=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_hash_index_on_field(self, collection: StandardCollection, fields: List[str], unique: bool):
        """
        add an hash index on the given fields

        :param collection: the collection where we need to create the index
        :param fields: the fields of the documents
        :param unique: true if you want to say that the values on the fields are unique
        :return:
        """
        collection.add_hash_index(fields=fields, unique=unique)

    def let_user_access_database(self, username: str, db_name: str):
        """
        Grant read/write access to a database for a user
        :param username: the name of the user involved
        :param db_name: the name of the database involved
        """
        self.sys_db.update_permission(username=username, permission='rw', database=db_name)

    def remove_collection(self, db: Database, collection_name: str):
        db.delete_collection(collection_name)

    def remove_document(self, collection: StandardCollection, document_key: int):
        """
        Remove a document in the collection
        :param collection: the collection invovled
        :param document_key: the key of the document to remove
        :return:
        """
        collection.delete(str(document_key))

    def has_database(self, db: str) -> bool:
        """
        check if the arango daemon has a database of a given name
        :param db: the name to check
        :return: true if the database exists, false otherwise
        """
        return self.sys_db.has_database(db)

    def has_collection(self, db: Database, collection_name: str) -> bool:
        """
        check if a collection exist in a given database
        :param db: the instance of the database to consider
        :param collection_name: the name of the collection to check
        :return: true if the collection exists inside the given db, false otherwise
        """
        return db.has_collection(collection_name)

    def has_document(self, collection: StandardCollection, document_key: int) -> bool:
        return collection.has(str(document_key))

    def get_all_collection_names(self) -> Iterable[str]:
        """

        :return: an iterable of all the name of collection inside the involved database
        """
        for x in self.database.collections():
            yield x['name']

    def get_all_documents_ks001_in_collection(self, collection: Collection) -> Iterable[int]:
        """

        :param collection: the collection to handle
        :return: the ks001 of all the documents inside this collection
        """
        for doc in collection:
            yield self._get_document_ks001(doc['_key'])

    def fetch_or_create_database(self, database_name: str) -> Database:
        """
        Fetch the given database or, if not existing, creates it
        :param database_name: the name of database to fetch
        :return: a database instance
        """
        if not self.has_database(database_name):
            self.sys_db.create_database(database_name, users=None)
        return self.client.db(database_name, username=self.username, password=self.password, verify=True)

    def fetch_or_create_collection(self, collection_name: str) -> StandardCollection:
        if not self.has_collection(db=self.database, collection_name=collection_name):
            logging.info(f"create collection '{collection_name}'...")
            self.database.create_collection(name=collection_name)
        return self.database.collection(name=collection_name)

    def fetch_or_create_document(self, collection: StandardCollection, document_key: int) -> Dict[str, Any]:
        """
        fetch the document with the set document _key or generates a new one with such a key

        :param collection: the collection where to store the document
        :param document_key: key of the document to fetch
        :return: the document itself
        """
        doc = collection.get(str(document_key))
        if doc is None:
            collection.insert({'_key': str(document_key)})
            doc = collection.get(str(document_key))
        return doc

    def update_document(self, collection: StandardCollection, doc: Dict[str, Any]):
        """
        updates a document prexisting in this collection
        :param collection:
        :param doc:
        :return:
        """
        collection.update(doc)

    def _get_document_ks001(self, doc_id: int) -> KS001Str:
        doc = self.ks001_to_collection.get(str(doc_id))
        if doc is None:
            raise ValueError(f"mismatch outcome!")
        else:
            return doc["ks001"]

    def _get_document_id(self, ks001: KS001Str) -> int:
        """

        :param ks001: the string (in format ks001) to handle
        :return: the collection id of the given ks001 string. unique among all ks001 values
        """

        docs = list(self.database.aql.execute(
            f"""FOR doc IN `{ArangoDB.KS001_TO_COLLECTIONID_NAME}` FILTER doc.`ks001` == @val RETURN doc""",
            bind_vars={
                'val': ks001},
            batch_size=2,
            count=True
        ))

        if len(docs) > 1:
            raise ValueError(f"too many documents fetched!")
        elif len(docs) == 1:
            return docs[0]['_key']
        else:
            # we add a new translation
            # create a new (temporary) documenht
            logging.debug(f"creating new key for ks001 {ks001}")
            metadata = self.ks001_to_collection.insert({'ks001': ks001})
            key = metadata['_key']
            return key


class AbstractArangoDBResource(IResourceManager, abc.ABC):

    def _is_path_in_collection_name(self, path: str, collection_name: str) -> bool:
        collection_name = collection_name.replace(".", "")
        path = commons.expand_string(path, [('/', '-')])
        return path in collection_name

    def _is_data_type_in_collection_name(self, data_type, collection_name: str) -> bool:
        return collection_name.endswith(f"-{data_type}")

    def _get_collection_name(self, path: str, data_type: str) -> str:
        """
        the collection name where the resource will be saved into

        :param path: path of the resource to save
        :param data_type: type of the resource to save
        :return:
        """

        # since arango can't store collection names with '/' inside but the path contains it! We convert every '-' into
        # we also need to save
        path = path.replace(".", "")
        path = commons.expand_string(path, [('/', '-')])
        return f"{path}-{data_type}"

    def _get_document_name(self, datasource: "ArangoDB", ks001: KS001Str) -> int:
        """
        ArangoDB can't store long collection names (up to 64 characters) but we would like to store the KS001
        representation as name. So we used numbers as names and we create a middle collection which represents
        the mapping between these 2. The number is prepended by the path and as suffix the datatype.

        :param ks001:
        :return:
        """
        return datasource._get_document_id(ks001)

    def is_compliant_with(self, datasource: "IDataSource") -> bool:
        return isinstance(datasource, ArangoDB)

    def get_all(self, datasource: "IDataSource", path: str = None, data_type: str = None) -> Iterable[Tuple[str, str, str]]:
        assert isinstance(datasource, ArangoDB)

        for collection_name in datasource.get_all_collection_names():
            if path is not None and not self._is_path_in_collection_name(path, collection_name):
                continue
            if data_type is not None and not self._is_data_type_in_collection_name(data_type, collection_name):
                continue
            for doc_ks001 in datasource.get_all_documents_ks001_in_collection(datasource.database[collection_name]):
                yield (path, doc_ks001, data_type)

    def remove(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str):
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)
        doc_name = self._get_document_name(datasource, ks001)
        collection = datasource.fetch_or_create_collection(collection_name)
        if datasource.has_document(collection, document_key=doc_name):
            datasource.remove_document(collection, document_key=doc_name)
        else:
            raise ResourceNotFoundError(f"resource {collection_name}/{doc_name} (aka {path}/{ks001}/{data_type}) not found")

    def contains(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> bool:
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)
        collection = datasource.fetch_or_create_collection(collection_name)
        doc_name = self._get_document_name(datasource, ks001)
        return datasource.has_document(collection, doc_name)


class BinaryArangoDB(AbstractArangoDBResource):

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def save_at(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str, content: Any):
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)

        collection: StandardCollection = datasource.fetch_or_create_collection(collection_name)
        doc_name = self._get_document_name(datasource, ks001)
        doc = datasource.fetch_or_create_document(collection=collection, document_key=doc_name)

        doc['data'] = content
        datasource.update_document(collection, doc)

    def get(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Any:
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)
        collection = datasource.fetch_or_create_collection(collection_name)

        doc_name = self._get_document_name(datasource, ks001)
        if not datasource.has_document(collection, doc_name):
            raise ResourceNotFoundError(f"resource {collection_name}/{doc_name} (aka {path}/{ks001}/{data_type}) not found")
        else:
            doc = datasource.fetch_or_create_document(collection, doc_name)
            return doc['data']

    def iterate_over(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Iterable[Any]:
        for c in self.get(datasource, path, ks001, data_type):
            yield c


class CsvArangoDB(AbstractArangoDBResource, AbstractCsvResourceManager):

    def _on_attached(self, datasource: "IDataSource"):
        pass

    def save_at(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str, content: Any):
        assert isinstance(datasource, ArangoDB)
        collection_name = self._get_collection_name(path, 'csv')

        collection = datasource.fetch_or_create_collection(collection_name)
        doc_name = self._get_document_name(datasource, ks001)
        doc = datasource.fetch_or_create_document(collection, doc_name)

        doc['header'] = []
        doc['data'] = []
        csv_reader = csv.DictReader(content.splitlines(), delimiter=',', quotechar='|')
        if len(doc['header']) == 0:
            doc['header'].extend(list(csv_reader.fieldnames))
        for row in csv_reader:
            tmp = []
            for key in row:
                tmp.append(row[key])
            doc['data'].append(tmp)

        datasource.update_document(collection, doc)

    def get(self, datasource: "IDataSource", path: str, ks001: KS001Str, data_type: str) -> Any:
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, 'csv')
        collection = datasource.fetch_or_create_collection(collection_name)

        doc_name = self._get_document_name(datasource, ks001)
        if not datasource.has_document(collection, doc_name):
            raise ResourceNotFoundError(f"resource {collection_name}/{doc_name} (aka {path}/{ks001}/csv) not found")
        else:
            doc = datasource.fetch_or_create_document(collection, doc_name)
            header = doc['header']
            result = ",".join(header) + "\n"
            for row in doc['data']:
                result += ",".join(row) + "\n"
            return result

    def head(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> Dict[str, Any]:
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)
        doc_key = self._get_document_name(datasource, ks001)
        for doc in datasource.database.aql.execute(f"""
                   FOR doc IN `{collection_name}` FILTER doc._key == "{doc_key}" RETURN [doc.header, doc.data[{index}]]
                """):
            header = doc[0]
            row = doc[1]
            return {header[i]: row[i] for i in range(len(header))}

    def tail(self, datasource: "IDataSource", path: PathStr, ks001: KS001Str, data_type: DataTypeStr, index: int) -> Dict[str, Any]:
        assert isinstance(datasource, ArangoDB)

        collection_name = self._get_collection_name(path, data_type)
        doc_key = self._get_document_name(datasource, ks001)
        for doc in datasource.database.aql.execute(f"""
                   FOR doc IN `{collection_name}` FILTER doc._key == "{doc_key}" RETURN [doc.header, doc.data[-{index}]]
                """):
            header = doc[0]
            row = doc[1]
            return {header[i]: row[i] for i in range(len(header))}
