import abc
import copy
import enum
import logging
import os
import re
from typing import Any, Tuple, Iterable, Union, Dict, List, Optional

from phdTester import commons


class LexicalError(Exception):
    pass


class Symbol(enum.Enum):
    COLON = enum.auto(),
    PIPE = enum.auto(),
    UNDERSCORE = enum.auto(),
    EQUAL = enum.auto(),
    STRING = enum.auto()

    def __str__(self):
        return self.name


class Aliases(commons.SlottedClass):
    """
    Structure allowing you to map an official name with an "alias", which is just a synonym of the actual name.
    Names and aliases are unique in this structure
    """

    __slots__ = ('_aliases', )

    def __init__(self, d: Dict[str, str] = None):
        self._aliases = {}
        if d is not None:
            for k, v in d.items():
                self.set_alias(k, v)

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, Aliases):
            return False
        return self._aliases == other._aliases

    def __iter__(self) -> Iterable[str]:
        """

        :return: iterable of officiale names
        """

        return iter(self._aliases)

    def aliases(self) -> Iterable[str]:
        """

        :return: iterable of aliases
        """
        return iter(self._aliases.values())

    def names(self) -> Iterable[str]:
        """

        :return: iterable of official names
        """
        return iter(self._aliases.keys())

    def has_alias(self, alias: str) -> bool:
        """
        check if we have defined an officiale name with a certain alias
        :param alias: the alias to check
        :return: true if there is an official name which alias is `alias`
        """
        return alias in self._aliases.values()

    def has_name(self, name: str) -> bool:
        """
        ::note
        This function will return false even if `name` is indeed an official name: this is the case
        when the user has setup no alias for it

        :param name: tghe name to check
        :return: True if the user has setup an alias for the official name `name`. False otherwise
        """
        return name in self._aliases

    @commons.inputs_not_none("name", "alias")
    def set_alias(self, name: str, alias: str):
        """
        set a new alias in this structure

        ::note
        It is considered error to have 2 same names and 2 same aliases in the same
        structure. It is considered error to set the alias of the same name more than once; the only
        exception is when the new alias is the same of the old one.

        :param name: the official name to add
        :param alias: the alias to add
        :return:
        """
        if name in self._aliases and self._aliases[name] == alias:
            return
        if self.has_name(name):
            raise ValueError(f"the name {name} is already present!")
        if self.has_alias(alias):
            raise ValueError(f"the alias {alias} is already present!")
        self._aliases[name] = alias

    def get_alias(self, name: str) -> str:
        return self._aliases[name]

    def get_name(self, alias: str) -> str:
        for k in self._aliases:
            if self._aliases[k] == alias:
                return k
        else:
            raise KeyError(f"alias {alias} has not real name in this structure!")

    def get_actual_name(self, string: str) -> str:
        """
        tries to fetch the correct name of the given string

        We do not know if the string is already an official name. We don't even know if the user
        has setup an alias for the string. So we:
         - return the official name if an alias has been setup and `string` is the alias
         - return `string` if an alias has been setup and `string` is the official name
         - return `string` if no alias has been setup for `string`, so we assume it's the official name
        :param string: the string the user has given us
        :return: the official name of `string`
        """

        return self.get_name_from_unsure(string, return_if_not_found=True)

    def get_name_from_unsure(self, string: str, return_if_not_found: bool = False) -> str:
        """
        the function simply returns if string is indeed an official name

        :param string: a string that you don't know if it's an alias or a name
        :param return_if_not_found: if true we will return string if the name couldn't be found.
            Otherwise we raise KeyError exception
        :return: the actual name
        """
        if self.has_name(string):
            return string
        elif self.has_alias(string):
            return self.get_name(alias=string)
        else:
            if return_if_not_found:
                return string
            else:
                raise KeyError(f"string {string} is neither a name nor an alias!")

    def get_alias_from_unsure(self, string: str) -> str:
        """
        generate the alias associated to this string.

        the function simply returns if string is indeed an alias

        :param string: a string that you don't know if it's an alias or a name
        :return: the alias associated to the given string.
        """
        if self.has_name(string):
            return self.get_alias(string)
        elif self.has_alias(string):
            return string

    def get(self, name: str = None, alias: str = None) -> str:
        if name is None and alias is None:
            raise ValueError(f"you need to specify either name or alias!")
        if name is not None and alias is not None:
            raise ValueError(f"you need to specify either name or alias!")
        if name is not None:
            return self.get_alias(name)
        if alias is not None:
            return self.get_name(alias)
        raise ValueError(f"impossible scenario! name={name} alias={alias}")


class IKS001ValueParser(abc.ABC):
    """
    Objects implementing this interface can be used to parse values from a string representation of a KS001
    """

    @abc.abstractmethod
    def parse(self, identifier: Optional[str], index: int, label: Optional[str], key: str, value: str) -> Any:
        """

        :param identifier: identifier of the KS001
        :param index: index of the dictionary where the value we need to parse is located
        :param label: label of the dictionary where the values we need to parse is located
        :param key: actual name of the value we need to parse
        :param value: string representation of the value we need to parse
        :return: the parsed value
        """
        pass


class KS001(commons.SlottedClass, IKS001ValueParser):
    """
    KS001 defines how a filename of an experiment should be named.

    Specification
    =============

    The standard is the following (written in python regex):

    given 4 **special characters** called:
     - =: separator between a key and a value;
     - _: separator between different key/value mapping
     - |: separator of dictionaries
     - :: separator between names and dictionaries

    filename := identifier? '|' dictionaries '|' extension?
    dictionaries := dictionary ( '|' dictionaries )*
    dictionary := name ':' keyvalues* | keyvalues
    keyvalues := keyvalue  ( '_' keyvalues )*
    keyvalue := key '=' value

    name := string
    identifier := [^|]+
    extension := string
    key := string
    value := string

    string := ([^=_|:]|'='{2}|'_'{2}|'|'{2}|':'{2})+

    In practice, here's some examples:

    |a=5|.png
    |basic:a=5|.png
    |basic:a=5_b=3|c=4|.png
    myIdentifier|basic:a=5_b=3|c=4|.png

    If you need to put a special characters inside either the name, key or value double them. For example:

    |a::=5|||.png

    Here the key is "a:" while the value is 5|

    Escaping characters are interpreted greedly (as soon as possible), hence

    |a===5|.png

    has a key equal to "a=" and a value of 5 and it is **not** intepreted as a key "a" and a value of "=5".

    The KS001 represents a **ordered** list of dictionaries (optionally named with a label called "identifier") containing
    an **ordered set** of key-value mapping.
    Key are string. value needs to be a string convertable element.
    The mappings are ordered by **key**: This means that the order is decided by the key alphanumeric value,
    so for example the "abc" always comes first of the key "cba". Key duplication is not permitted.
    Neither key nor values cannot be None


    File extensions are explicitly outside the dictionary.

    Unnamed Dictionaries
    ====================

    Unnamed dictionaries cannot be empty. Consider this scenario:

    |a=5|||.png

    it's should be interpreted as a="5|" or as a=5 (and then there are 2 empty dictionaries?)
    To solve this issue we explictly avoid empty unnamed dictionaries. You can however have an empty named dictionary,
    like the following one:

    |a=5|empty:|.png

    Aliases
    =======

    KS001 directly supports aliasing. Aliases is introduced because dictionaries can be big, hence the generated string
    may be long. Since several filesystem does not allow for lengthy filename, aliasing is required.

    Aliases are mapping of key names into shorter keynames.
    You can set aliases both on keys and on values. For example if you have set "f" as an alias of "foo", both
    this dictionaries are semantically the same:

    |a=5_foo=3|.png

    |a=5_f=3|.png

    As for the keys, no alias can have a None value

    """

    __slots__ = ('key_aliases', 'value_aliases', 'identifier', 'dicts', )

    def __init__(self, identifier: str = None):
        """
        Create a new KS001, representing an ordered list of dictionaries, optionally named
        :param identifier: the name of of this structure
        """
        self.key_aliases = Aliases()
        self.value_aliases = Aliases()
        self.identifier = identifier
        self.dicts: List[Dict[str, Union[str, Dict[str, Any]]]] = []
        """
        list of dictionaries. 
        
        Each value is a dicitonary with 2 keys
        - name: the name of ther dictionary (None if it has no name)
        - dict: the dictionary to represent
        
        dict values are dictionaries where each key is a key of the mapping while each value is a value of the mapping
        dict are **unordered**
        """

    def clone(self) -> "KS001":
        """
        Perform a deep clone of the structure

        The values of the dictionaries are copied by calling copy.copy() functions
        :return: the new clone of the structure
        """
        result = KS001(identifier=self.identifier)
        for k in self.key_aliases:
            result.key_aliases.set_alias(k, self.key_aliases.get_alias(k))
        for k in self.value_aliases:
            result.value_aliases.set_alias(k, self.value_aliases.get_alias(k))
        for d in self.dicts:
            created = result._add_dict(name=d["name"])
            for k in d["dict"]:
                created[k] = copy.copy(d["dict"][k])
        return result

    @commons.inputs_not_none("other")
    def __add__(self, other: "KS001") -> "KS001":
        """
        Creates a new KS001 generated by appending the second one to the tail of the first one

        ::note
        the inputs won't be altered at all

        :param other:
        :return: a new instance of KS001 with the new fields
        """

        result = self.clone()
        return result.append(other)

    @commons.inputs_not_none("other")
    def __iadd__(self, other: "KS001"):
        """
        Updates the current KS001 by adding to the end of self the data from the other KS001

        ::note
        This will change `self` object

        :param other:
        :return:
        """
        self.append(other)

    @commons.inputs_not_none("other")
    def append(self, other: "KS001") -> "KS001":
        """
        Append a KS001 at the end of another one

        note::
        This will change the `self` object

        Every dict in the `other` structure will be copied into the self value.
        `other` identifier is ignored. Aliases are copied as well

        We put not the values of `other`, but clones of `other` values, generated via copy.copy() function

        :param other: the KS001 to append at the end of this structure
        :return: the new update KS001 version.
        """

        for k in other.key_aliases:
            self.key_aliases.set_alias(k, other.key_aliases.get_alias(k))
        for k in other.value_aliases:
            self.value_aliases.set_alias(k, other.value_aliases.get_alias(k))
        for d in other.dicts:
            if d["name"] is not None:
                new_dict = self._try_and_generate_dict_name(d["name"])
            else:
                new_dict = self._try_and_generate_dict_index(len(self.dicts))
            for k in d["dict"]:
                new_dict[k] = copy.copy(d["dict"][k])

        return self

    @commons.inputs_not_none("item")
    def __getitem__(self, item: Union[int, str]) -> Dict[str, str]:
        if isinstance(item, str):
            for d in self.dicts:
                if d["name"] == item:
                    return d["dict"]
        elif isinstance(item, int):
            return self.dicts[item]["dict"]
        else:
            raise TypeError(f"invalid key type {type(item)}! Only str or int accepted!")

    def __len__(self) -> int:
        return len(self.dicts)

    def __repr__(self) -> str:
        return str(self)

    def __contains__(self, other: "KS001") -> bool:
        """
        Checks if a KS001 is contained into another one

        ::note
        a structure `other` is contained in a `self` KS001 only if it exists a dictionary in `self` such that
        it contains all the key-mappings present in `other`. if `other` contains multiple dictionary, all the
        dictionaries must be present in `self`. labels, identifiers and indices are ignroe during contain
        procedure.

        :param other: the other KS001 structure to look for
        :return: true if all the key-values of self are contained in other.
                False otherwise
        """

        for other_dict in other.dicts:
            found = True
            for i, self_dict in enumerate(self.dicts):
                found = True
                for k, v in other_dict["dict"].items():
                    if k not in self_dict["dict"]:
                        found = False
                        break
                    if v != self_dict["dict"][k]:
                        found = False
                        break

            if found is False:
                return False

        return True

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, KS001):
            return False
        if self.identifier != other.identifier:
            return False
        if self.key_aliases != other.key_aliases:
            return False
        if self.value_aliases != other.value_aliases:
            return False
        return self.dicts == other.dicts

    def _add_dict(self, name: str = None) -> Dict[str, str]:
        """
        Adds a new dictionary in the KS001
        :param name: the label of the dictionary. None if you want to create an unnamed dictionary
        :return: the dictionary which sould contain key-value mappings just created
        """
        result = {}
        self.dicts.append(dict(name=name, dict=result))
        return result

    def _has_dict_index(self, index: int) -> bool:
        return index < len(self.dicts)

    def _has_dict_name(self, name: str) -> bool:
        for d in self.dicts:
            if d['name'] == name:
                return True
        else:
            return False

    def _has_dict_place(self, place: Union[str, int]) -> bool:
        if isinstance(place, int):
            return self._has_dict_index(place)
        elif isinstance(place, str):
            return self._has_dict_name(place)
        else:
            raise TypeError(f"invalid type {type(place)} for place. Needs str or int!")

    def has_key_value(self, k: str, v: Any) -> bool:
        for d in self.dicts:
            if k in d["dict"] and d["dict"][k] == v:
                return True
        else:
            return False

    def has_key_in(self, place: Union[str, int], key: str) -> bool:
        """
        Checks if the KS001 has a particular key in a particular place
        :param place: an identifier for the dictionary. May be either the index or the label
        :param key: the key of the mapping
        :return: true if the KS001 structure has the key `k` in the dictionary identified by `place`
        """

        return self._has_dict_place(place) and key in self[place]

    @commons.inputs_not_none("place", "k", "v")
    def has_key_value_in(self, place: Union[str, int], k: str, v: Any) -> bool:
        """
        Checks if the KS001 has a particular mapping in a particular place
        :param place: an identifier for the dictionary. May be either the index or the label
        :param k: the key of the mapping
        :param v:  the vlaue of the mapping to check
        :return: true if the KS001 structure has the mapping `k`-`v` in the dictionary identified by `place`
        """
        return self._has_dict_place(place) and k in self[place] and self[place][k] == v

    @commons.inputs_not_none("place", "key")
    def get_value_of_key_in(self, place: Union[str, int], key: str, none_if_fail: bool = False) -> Any:
        if none_if_fail:
            if not self._has_dict_place(place):
                return None
            if key not in self[place]:
                return None
        return self[place][key]

    def _try_and_generate_dict_index(self, index: int) -> Dict[str, str]:
        while True:
            if len(self.dicts) <= index:
                self._add_dict()
            else:
                break

        return self[index]

    def _try_and_generate_dict_name(self, name: str) -> Dict[str, str]:
        if self._has_dict_name(name):
            return self[name]
        else:
            return self._add_dict(name)

    @commons.inputs_not_none("place", "key", "value")
    def add_key_value(self, place: Union[str, int], key: str, value: Any) -> "KS001":
        if isinstance(place, int):
            d = self._try_and_generate_dict_index(place)
        elif isinstance(place, str):
            d = self._try_and_generate_dict_name(place)
        else:
            raise TypeError(f"invalid type {place}! allowed types are int or str")
        d[key] = value
        return self

    @commons.inputs_not_none("place", "key", "value")
    def remove_key_value(self, place: Union[str, int], key: str, value: Any) -> "KS001":
        if key not in self[place]:
            return self
        if self[place][key] != value:
            return self
        if isinstance(place, int) and len(self[place][key]) == 1 and self.dicts[place]["name"] is None:
            # if this is the last key we're removing in an unnamed dictionary we raise error since an unnamed dictionary
            # cannot be empty
            raise ValueError(f"trying to generate an empty unnamed dictionary!")
        del self[place][key]
        return self

    @commons.inputs_not_none("name")
    def add_empty_dictionary(self, name: str) -> "KS001":
        self._try_and_generate_dict_name(name)
        return self

    @commons.inputs_not_none("actual_name", "alias")
    def add_key_alias(self, actual_name: str, alias: str):
        self.key_aliases.set_alias(actual_name, alias)

    @commons.inputs_not_none("aliases")
    def add_key_aliases(self, aliases: Dict[str, str]):
        for k in aliases:
            self.key_aliases.set_alias(k, aliases[k])

    @commons.inputs_not_none("actual_value", "alias")
    def add_value_alias(self, actual_value: str, alias: str):
        self.value_aliases.set_alias(actual_value, alias)

    @commons.inputs_not_none("aliases")
    def add_values_aliases(self, aliases: Dict[str, str]):
        for k in aliases:
            self.value_aliases.set_alias(k, aliases[k])

    def __str__(self) -> str:
        result = []
        for i, d in enumerate(self.dicts):
            keymapping = "\n".join(map(lambda x: "=".join([x[0], str(x[1])]), d["dict"].items()))
            result.append("index={}, name=\"{}\"\n{}".format(
                i,
                d["name"] if d["name"] is not None else "",
                keymapping
            ))
        return "\n".join(result)

    @classmethod
    def get_from(cls, d: Dict[Any, Any], identifier: str = None, label: str = None, key_alias: Dict[str, str] = None, value_alias: Dict[str, str] = None):
        """
        Generates a new structure starting from a dictionary

        the KS001 structure generated will have onlyl one dictionary

        :param d: the dictionary involved
        :param identifier: optional identifier of the KS001 to generate. None if you don't want an identifier
        :param label: optional label of the KS001 dictionary to generate
        :param key_alias: representing alias of keys
        :param value_alias: representing alias of values
        :return: a new KS001 object
        """

        result = KS001(identifier=identifier)

        if key_alias is not None:
            for k, v in key_alias.items():
                result.add_key_alias(str(k), str(v))

        if value_alias is not None:
            for k, v in value_alias.items():
                result.add_value_alias(str(k), str(v))

        for k, v in d.items():
            if key_alias is not None:
                k = result.key_aliases.get_alias_from_unsure(k)
            if value_alias is not None:
                v = result.value_aliases.get_actual_name(v)

            if label is None:
                result.add_key_value(place=0, key=str(k), value=v)
            else:
                result.add_key_value(place=label, key=str(k), value=v)
        return result

    def dump_str(self, use_key_alias: bool = True, use_value_alias: bool = True, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "=") -> str:
        """
        Generate a string representing this structure. This string can be parser by :parse_str: function

        :param use_key_alias: if set, we will try to use alias name to generate the keys in the filename
        if available.
        If False, we will always use to official name during the string dumping
        :param use_value_alias: if set, we will try to use alias name to generate the values in the filename
        if available.
        If False, we will always use to official name during the string dumping
        :param colon: the character to put between dictionary label and dictionary key mapping
        :param pipe: the character to put between dictionaries
        :param underscore: the character to put between key-value mappings
        :param equal: the character to put between key and value
        :return: a string which can be parsed with this structure
        """

        def sanitize(string: str, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "=") -> str:
            result = ""
            for c in string:
                if c in [colon, pipe, underscore, equal]:
                    # escape special characters
                    result += c * 2
                else:
                    result += c
            return result

        result = ""
        if self.identifier is not None:
            result += str(sanitize(self.identifier, colon, pipe, underscore, equal))
        result += pipe
        for d in self.dicts:
            if d["name"] is not None:
                result += sanitize(d["name"], colon, pipe, underscore, equal) + colon
            tmp = []
            for key in sorted(d["dict"].keys()):
                value = d["dict"][key]
                if use_key_alias and self.key_aliases.has_name(key):
                    key = self.key_aliases.get_alias(key)
                if use_value_alias and self.value_aliases.has_name(value):
                    value = self.value_aliases.get_alias(value)
                key = sanitize(key, colon, pipe, underscore, equal)
                value = sanitize(str(value), colon, pipe, underscore, equal)
                tmp.append(key + equal + value)
            result += underscore.join(tmp)
            result += pipe
        return result

    def dump_filename(self, dir_name: str = None, extension: str = None, use_key_alias: str = True, use_value_alias: str = True, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "="):
        """
        Generate a filename specified by this KS001

        for example, running

        self.dump_filename("/home/", "png")

        will generate a file called "/home/|a=5|.png"

        :param dir_name: the directory containing this filename
        :param extension: the extension of this filename
        :param use_key_alias:
        :param use_value_alias:
        :param colon:
        :param pipe:
        :param underscore:
        :param equal:
        :return:
        """

        path = self.dump_str(use_key_alias, use_value_alias, colon, pipe, underscore, equal)
        if extension is not None:
            path = path + "." + extension
        if dir_name is not None:
            path = os.path.join(dir_name, path)
        return os.path.abspath(path)

    def parse(self, identifier: Optional[str], index: int, label: Optional[str], key: str, value: str) -> Any:
        if re.match(r"^[Tt][Rr][Uu][Ee]$", value):
            return True
        elif re.match(r"^[Ff][Aa][Ll][Ss][Ee]", value):
            return False
        elif re.match(r"^[+\-]?\d+\.\d+$", value):
            return float(value)
        elif re.match(r"^[+\-]?\d+$", value):
            return int(value)
        else:
            return str(value)

    @classmethod
    def parse_filename(cls, filename: str, key_alias: Union[Dict[str, str], Aliases] = None, value_alias: Union[Dict[str, str], Aliases] = None, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "=", value_parsing_function: IKS001ValueParser = None):
        """


        :param filename: filename of a file. May have an extension. May be absolute or relative
        :return: a structure representing a KS001
        """

        filename = os.path.basename(filename)
        # trash away the extension
        filename, _, _ = filename.rpartition(pipe)
        filename = filename + pipe

        return cls.parse_str(filename, key_alias, value_alias, colon, pipe, underscore, equal, value_parsing_function)

    @classmethod
    def parse_str(cls, string: str, key_alias: Union[Dict[str, str], Aliases] = None, value_alias: Union[Dict[str, str], Aliases] = None, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "=", value_parsing_function: IKS001ValueParser = None):

        class State(enum.Enum):
            INIT = enum.auto(),
            "We have just started the parsing. We may fill the identifier. We still need to create the first dict"
            NEW_DICT = enum.auto(),
            "We have detected a new |, so we need to start the creation of a dict"
            NEW_PAIR = enum.auto(),
            "We are inside the procedure that is generating a new key-mapping from the string"
            END_PAIR = enum.auto(),
            "We have just finished adding a new key-value mapping"

        dictionary_label: str = None
        dictionary_to_create_id = 0

        state: State = State.INIT

        key_str: str = None
        "contains the key of a keymapping we want to add"
        value_str: str = None
        "contains the value of a keymapping we want to add"
        next_string_is_key = False
        """If true it means the next string we read should be interpreted as a key. 
        Mutually exclusive with next_string_is_value. Used only when state is NEW_PAIR"""
        next_string_is_value = False
        """If true if means the enxt string we read should be interpreted as a value.
        Mutually exclusive with next_string_is_key. Used only when state is NEW_PAIR"""

        result = cls()
        if key_alias is not None:
            if isinstance(key_alias, Aliases):
                result.key_aliases = key_alias
            elif isinstance(key_alias, dict):
                for k in key_alias:
                    result.key_aliases.set_alias(k, key_alias[k])
            else:
                raise TypeError(f"invalid type {type(key_alias)}! Only Aliases and dict accepted!")
        if value_alias is not None:
            if isinstance(value_alias, Aliases):
                result.value_aliases = value_alias
            elif isinstance(value_alias, dict):
                for k in value_alias:
                    result.value_aliases.set_alias(k, value_alias[k])
            else:
                raise TypeError(f"invalid type {type(key_alias)}! Only Aliases and dict accepted!")

        for symbol, value, index in cls._symbol_generator(string, colon, pipe, underscore, equal):
            if state in [State.INIT, ]:
                if symbol == Symbol.STRING:
                    result.identifier = value
                elif symbol == Symbol.PIPE:
                    state = State.NEW_DICT
                else:
                    raise ValueError(f"expected either string or pipe after {index}, got {symbol}! string was \"{string}\"!")
            elif state in [State.NEW_DICT, ]:
                if symbol == Symbol.STRING:
                    # we have just read a |. And now we have a string. This string can either be the dicitonary name
                    # or the first key of the dictionary. We need to suspend our decision to the next cycle.
                    first_string = value
                elif symbol == Symbol.EQUAL:
                    # ok, first_string was actually the key of the first pair. We switch state
                    key_str = first_string
                    next_string_is_key = False
                    next_string_is_value = True
                    state = State.NEW_PAIR
                elif symbol == Symbol.COLON:
                    # ok, the first_string was actually the label of the dictionary
                    dictionary_label = first_string
                    # now we are sure to expect a new pair
                    state = State.NEW_PAIR
                    next_string_is_key = True
                    next_string_is_value = False
                else:
                    raise ValueError(f"Error while parsing a dictionary. We expected either a string, equal but received {symbol} ({value})")
            elif state in [State.NEW_PAIR, ]:
                # we can enter after we have detected a = at the first key-value mapping
                # or we can enter after we still need to read the key. None the less the first time we enter here we
                # should expect a string
                if symbol == Symbol.STRING:
                    if next_string_is_key and next_string_is_value:
                        raise ValueError(f"we can't decide if the next string \"{value}\" is either a key or a value!")
                    if not next_string_is_key and not next_string_is_value:
                        raise ValueError(f"we can't decide if the next string \"{value}\" is either a key or a value!")
                    if next_string_is_key:
                        key_str = value
                        # we still need to fetch the value
                    if next_string_is_value:
                        value_str = value
                        # ok, we have completed a mapping. adding it

                        key_str = result.key_aliases.get_name_from_unsure(key_str, return_if_not_found=True)
                        value_str = result.value_aliases.get_name_from_unsure(value_str, return_if_not_found=True)
                        # if the value parser is present, call it. Otherwise just use the default one
                        if value_parsing_function is not None:
                            parser = value_parsing_function
                        else:
                            parser = result
                        value = parser.parse(result.identifier, dictionary_to_create_id, dictionary_label, key_str, value_str)
                        if dictionary_label is not None:
                            result.add_key_value(place=dictionary_label, key=key_str, value=value)
                        else:
                            result.add_key_value(place=dictionary_to_create_id, key=key_str, value=value)
                        # ok, we have finished a pair, let's change the state
                        state = State.END_PAIR
                elif symbol == Symbol.EQUAL:
                    # when we enter here we should already have a key_str
                    if key_str is None:
                        raise ValueError(f"bug inside the parser when decoding the = at {index}. We should already have a key!")
                    next_string_is_key = False
                    next_string_is_value = True
                elif symbol == Symbol.PIPE:
                    # happens when there is a named dictionary which is empty.
                    # we need to create an empty dictionary and switch to the NEW_DICT state
                    # we need to do mothing and switch again
                    if dictionary_label is None:
                        raise ValueError(f"Trying to generate an empty unnamed dicitonary. This is not allowed")
                    key_str = None
                    value_str = None
                    next_string_is_key = True
                    next_string_is_value = False
                    result.add_empty_dictionary(dictionary_label)
                    state = State.NEW_DICT

                else:
                    raise ValueError(f"Unexpected symbol {symbol} ({value}) at {index}. We are genreating a new pair!")
            elif state in [State.END_PAIR, ]:
                # we enter here as soon as we finished a pair
                if symbol == Symbol.UNDERSCORE:
                    # the dictionary still continues! We're goingot create a new pair, hence we need to return to NEW_PAIR
                    # the next string is sutre to be a key!
                    key_str = None
                    value_str = None
                    next_string_is_key = True
                    next_string_is_value = False
                    state = State.NEW_PAIR
                elif symbol == Symbol.PIPE:
                    # ok, we've finished handling this dictionary. The next character may either be a string
                    # representing a new different dictionary or there may be no other character.

                    key_str = None
                    value_str = None
                    next_string_is_key = False
                    next_string_is_value = False

                    dictionary_to_create_id += 1
                    dictionary_label = None
                    first_string = None
                    state = State.NEW_DICT
                else:
                    raise ValueError(f"unexpecxted symbol {symbol} ({value}) at {index}. Expecting _ or |")

            else:
                raise ValueError(f"invalid parsing! Error at {index} after fetching {value} which we interpreted as {symbol}!")

        return result

    # TODO use lark for parsing
    # @classmethod
    # def parse_str(cls, string: str, key_alias: Union[Dict[str, str], Aliases] = None,
    #               value_alias: Union[Dict[str, str], Aliases] = None, colon: str = ":", pipe: str = "|",
    #               underscore: str = "_", equal: str = "=", value_parsing_function: IKS001ValueParser = None):
    #     collision_grammar = f"""
    #         start: filename
    #         filename: identifier? "{pipe}" dictionaries "{pipe}" extension?
    #         dictionaries: dictionary ( "{pipe}" dictionaries )*
    #         dictionary: name "{colon}" keyvalues* | keyvalues
    #         keyvalues: keyvalue  ( "{underscore}" keyvalues )*
    #         keyvalue: key "{equal}" value
    #
    #         name: STRING
    #         identifier: STRING
    #         extension: STRING
    #         key: STRING
    #         value: STRING
    #
    #         STRING: /([^{equal}{underscore}{pipe}{colon}]|"{equal}""{equal}"|"{underscore}""{underscore}"|"{pipe}""{pipe}"|"{colon}""{colon}")+/
    #         """
    #     logging.info(f"string is {string}")
    #     parser = lark.Lark(collision_grammar, parser='lalr', debug=True)
    #     ast = parser.parse(string)
    #
    #     logging.info("parsing complete!")

    @staticmethod
    def _symbol_generator(input: str, colon: str = ":", pipe: str = "|", underscore: str = "_", equal: str = "=") -> Tuple[Symbol, Any, int]:

        specials = [
            (colon, Symbol.COLON),
            (pipe, Symbol.PIPE),
            (underscore, Symbol.UNDERSCORE),
            (equal, Symbol.EQUAL)
        ]

        def get_symbol(s: str) -> Symbol:
            for ch, symbol in specials:
                if ch == s:
                    return symbol

        i = 0
        building_string = False
        value = ""
        while True:  # generator loop
            if i >= len(input):
                break

            is_last_character = i == (len(input)-1)

            if building_string:
                # we were already building a string
                if input[i] in map(lambda x:x[0], specials):
                    # detected a special character. We need to check if the next character is the same special one too
                    if is_last_character:
                        # there can't be a next symbol: so input[i] does not belong to this string
                        # we do not change i because we still need to read this special character
                        yield (Symbol.STRING, value, i)
                        building_string = False
                        value = ""
                    else:
                        # we check if input[i] is repeated twice
                        if input[i] == input[i+1]:
                            # append character
                            value += input[i]
                            i += 2
                        else:
                            # input[i] is an actual special character. End the string
                            # we do not change i because we still need to read this special character
                            yield (Symbol.STRING, value, i)
                            building_string = False
                            value = ""
                else:
                    # we didn't read a special character. Just add the character
                    value += input[i]
                    if is_last_character:
                        # if this is the last character of the string yield the building string
                        yield (Symbol.STRING, value, i)
                        building_string = False
                        value = ""
                    i += 1
            else:
                # not building string
                if input[i] in map(lambda x: x[0], specials):
                    # detected a special character. We need to check if the next character is the same special one too
                    if is_last_character:
                        # there can't be a next symbol
                        yield (get_symbol(input[i]), input[i], i)
                        building_string = False
                        i += 1
                        value = ""
                    else:
                        # we check if the next character is the same of input[i]. If so, this is a start of a string
                        if input[i] == input[i+1]:
                            # this is the beginning of a string
                            building_string = True
                            value += input[i]
                            i += 2
                        else:
                            # nope. this is a correct symbol
                            yield (get_symbol(input[i]), input[i], i)
                            building_string = False
                            i += 1
                            value = ""
                else:
                    # this is a normal character, so we need to say that we're creating a new string
                    building_string = True
                    value += input[i]
                    i += 1


