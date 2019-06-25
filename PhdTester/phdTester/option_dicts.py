from typing import Any, Iterable

from phdTester.model_interfaces import IOptionDict


class StandardOptionDict(IOptionDict):
    """
    Implementation of IOptionDict which directly queries all the public attributes of the object attached to it.

    Use only when:
     - the subtype has __dict__ attribute (if it's a class this is ensured by default)
     - the attributes you care about are public and are not properties (tagged with @proiperty)
     - it's not implemented as a tuple (so no __slots__ schenanigans)

     Use this class when the options are known a priori. To do that you need a class.
    """

    def _create_empty(self) -> "IOptionDict":
        result = self.__class__()
        for k in self.options():
            result.__dict__[k] = None
        return result

    def __init__(self):
        IOptionDict.__init__(self)

    def options(self) -> Iterable[str]:
        return (name for name in vars(self) if not name.startswith('_'))

    def get_option(self, name: str) -> Any:
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options (which are {list(self.options())})")
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        if not self.contains_option(name):
            raise KeyError(f"key {name} is not inside options (which are {list(self.options())})")
        self.__dict__[name] = value


class DefaultAnonymuousOptionObject(IOptionDict):
    """
    An OptionDict whose options are not retrieved from the declared fields in the class, but passed during constructor.

    Use this class when the options are not known apriori.
    """

    def _create_empty(self) -> "IOptionDict":
        return self.__class__(self.__dict__.keys())

    def __init__(self, fields: Iterable[str]):
        IOptionDict.__init__(self)
        for f in fields:
            self.__dict__[f] = None

    def options(self) -> Iterable[str]:
        return filter(lambda x: not x.startswith('_'), self.__dict__)

    def get_option(self, name: str) -> Any:
        if name not in self.__dict__:
            self.__dict__[name] = None
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        self.__dict__[name] = value


class DynamicOptionDict(IOptionDict):
    """
    An implementation of Option Dict where the values are dynamic: you can add and remove options as you wish

    An option is always containes in this dictionary and, if not present, the option will have the default value of None
    """

    def contains_option(self, name: str) -> bool:
        return True

    def options(self) -> Iterable[str]:
        return filter(lambda x: not x.startwith("_"), self.__dict__)

    def get_option(self, name: str) -> Any:
        if name not in self.__dict__:
            self.__dict__[name] = None
        return self.__dict__[name]

    def set_option(self, name: str, value: Any):
        self.__dict__[name] = value

    def _create_empty(self) -> "IOptionDict":
        return self.__class__()

    def __init__(self):
        IOptionDict.__init__(self)
