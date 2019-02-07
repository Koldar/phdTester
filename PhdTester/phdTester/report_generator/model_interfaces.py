import abc
from typing import Union, Iterable, Optional

from phdTester.commons import FileWriter


class ILatexLeafNode(abc.ABC):

    @property
    @abc.abstractmethod
    def unique_id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def type(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def parent(self) -> "ILatexNode":
        pass

    @parent.setter
    @abc.abstractmethod
    def parent(self, newvalue: "ILatexNode"):
        pass

    @abc.abstractmethod
    def begin_process(self, f: FileWriter, context: dict) -> Optional[dict]:
        pass

    @abc.abstractmethod
    def end_process(self, f: FileWriter, context: dict) -> Optional[dict]:
        pass

    @property
    def is_root(self) -> bool:
        return self.parent is None


class ILatexNode(ILatexLeafNode):

    @abc.abstractmethod
    def __iter__(self) -> Iterable["ILatexLeafNode"]:
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        pass

    @abc.abstractmethod
    def __getitem__(self, item: Union[str, int]) -> "ILatexLeafNode":
        pass

    @abc.abstractmethod
    def __setitem__(self, key: str, value: "ILatexLeafNode"):
        pass

    @abc.abstractmethod
    def begin_direct_child(self, f: FileWriter, i: int, child: "ILatexLeafNode", total_children: int, is_first:bool, is_last: bool, context: dict):
        pass

    @abc.abstractmethod
    def end_direct_child(self, f: FileWriter, i: int, child: "ILatexLeafNode", total_children: int, is_first: bool, is_last: bool, context: dict):
        pass

    def add_child(self, child: "ILatexNode") -> "ILatexNode":
        self[child.unique_id] = child
        return child

    def add_leaf_child(self, child: "ILatexLeafNode") -> "ILatexLeafNode":
        self[child.unique_id] = child
        return child

    def add_children(self, *children: "ILatexNode") -> Iterable["ILatexNode"]:
        for child in children:
            self.add_child(child)
        return children

    def add_leaf_children(self, *children: "ILatexLeafNode") -> Iterable["ILatexLeafNode"]:
        for child in children:
            self.add_leaf_child(child)
        return children

    @property
    def children_number(self):
        return len(self)

    def __iadd__(self, other: Union["ILatexNode", Iterable["ILatexNode"]]) -> "ILatexNode":
        """
        Alias of add_child/add_children
        :param other:
        :return: self
        """
        if hasattr(other, "__getitem__"):
            self.add_children(other)
        else:
            self.add_child(other)
        return self

