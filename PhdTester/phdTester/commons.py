import abc
import inspect
import logging
import multiprocessing
import re
import subprocess

from multiprocessing import Process
from typing import Any, Iterable, Callable, Union, Dict, Tuple, List


def inputs_not_none(*inputs: str):
    """
    Ensure that all the aprameters specified are not None

    The decorator works only for positional arguments, not keyword ones

    :param inputs: all the input to ensure that they are not None
    :raise ValueError: if a constraint is not valid
    :return:
    """

    def wrapper(func):
        def decorator(*args, **kwargs):
            params = inspect.getfullargspec(func)[0]
            positional_args = inspect.getfullargspec(func).args
            if len(positional_args) == 0:
                raise ValueError(f"inputs_not_none can work only with positional arguments!")
            # generate the actual values
            actual = {}
            for i, val in enumerate(args):
                actual[params[i]] = val
            for key, val in kwargs.items():
                actual[key] = val
            # test None
            for p in inputs:
                if actual[p] is None:
                    raise ValueError(f"parameter {p} in function {func.__name__} cannot be None!")
            return func(*args, **kwargs)

        return decorator

    return wrapper


def run_process(name: str = None, index: int = None):

    def start_and_wait():
        processes = []
        for f in run_process.functions:
            aname = name
            aindex = index
            if aname is None:
                aname = f.__name__
            if aindex is None:
                aindex = len(processes)
            p = multiprocessing.Process(name=f"{aname}_{aindex:02d}", target=f, args=(), kwargs={})
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def clear():
        run_process.functions.clear()

    def decorator_run_process(function):

        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        run_process.functions.append(function)
        return wrapper

    if "functions" not in run_process.__dict__:
        run_process.__dict__["functions"] = []

    run_process.start_and_wait = start_and_wait
    return decorator_run_process


def str_2_bool(s: str) -> bool:
    if s == "True":
        return True
    elif s == "False":
        return False
    else:
        raise ValueError(f"cannot convert {s} into boolean!")


def safe_eval(s: str) -> Any:
    """
    Execute a python string evaluating a mathematical expression
    :param s:
    :return:
    """
    # make a list of safe functions
    safe_list = ['math', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'cosh',
                 'degrees', 'e', 'exp', 'fabs', 'floor', 'fmod', 'frexp', 'hypot',
                 'ldexp', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin',
                 'sinh', 'sqrt', 'tan', 'tanh']
    # use the list to filter the local namespace
    safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
    # add any needed builtins back in.
    safe_dict['abs'] = abs
    safe_dict['range'] = range

    return eval(s, {"__builtins__": None}, safe_dict)


def distinct(it: Iterable[Any]) -> Iterable[Any]:
    unique = list()
    for v in it:
        if v not in unique:
            unique.append(v)
            yield v


class ExternalProgramFailureError(Exception):

    def __init__(self, exit_code: int, cwd: str, program: str):
        self.exit_code = exit_code
        self.cwd = cwd
        self.program = program

    def __str__(self):
        return f"""
        CWD= {self.cwd}
        PROGRAM = {self.program}
        EXIT CODE = {self.exit_code}
        """


class ProgramExecutor(abc.ABC):

    def __init__(self):
        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0

    def reset(self):
        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0

    def execute_external_program(self, program: Union[str, Iterable[str]], working_directory: str):
        self.reset()

        if isinstance(program, str):
            program_str = program
        elif isinstance(program, Iterable):
            program_str = " ".join(program)
        else:
            raise TypeError(f"program needs to be either str or iterable of str!")

        logging.info(f"{working_directory}: executing {program_str}")
        with subprocess.Popen(program_str, cwd=working_directory, stdout=subprocess.PIPE, shell=True) as proc:
            proc.wait()
            self.exit_code = proc.returncode
            self.stdout = str(proc.stdout.read(), 'utf8') if proc.stdout is not None else "",
            self.stderr = str(proc.stderr.read(), 'utf8') if proc.stderr is not None else ""

        if self.exit_code != 0:
            raise ExternalProgramFailureError(exit_code=self.exit_code, cwd=working_directory, program=program_str)

        return self.exit_code


def execute_on_multiple_process(num_process: int, function: Callable, it: Iterable, name_format: str):
    processes = {}

    next_process_id = 0
    for val in it:
        if len(processes) < num_process:
            process_id = next_process_id
            next_process_id += 1
            p = Process(target=function(val), name=name_format.format(process_id=process_id))
            processes[process_id] = p
            p.start()
        else:
            to_remove = set()
            for i, p in processes.items():
                # we check if it's alive
                if not p.is_alive():
                    # we remove the process
                    to_remove.add(i)
            for i in to_remove:
                del processes[i]

        for i, p in processes.items():
            p.join(timeout=0.2)


class FileWriter:

    def __init__(self, name: str, mode: str = "w"):
        self.name = name
        self.mode = mode
        self.f = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self.f = open(self.name, self.mode)

    def close(self):
        if self.f is None:
            raise ValueError(f"file has not been opened yet!")
        self.f.close()

    def write(self, template: str=None):
        if template is not None:
            self.f.write(template)

    def writeln(self, template: str=None):
        self.write(template)
        self.f.write("\n")


class RegexException(Exception):
    """
    exception to throw when a regex fails
    """
    pass


def float_range(x, y, step=1):
    tmp = x
    while tmp < y:
        yield tmp
        tmp += step


def parse_percentage_str(s: str) -> float:
    regex = r"(?P<percentage>\d+)\%"
    m = re.search(regex, s)
    if m is None:
        raise RegexException(f"string '{s}' can't be applied to regex '{regex}'!", regex)
    return float(m.group("percentage"))/100.


def parse_range(r: str) -> Tuple[float, float, bool, bool]:
    """
    Parse strings in the format of:

    [3,4]
    (3,4]
    ]3,4]
    [3,4(
    [3,4[

    :param r: the string to parse
    :return: 4 value representing, respectively, the interval lowerbound, the interval upperbound, wether the
    lowerbound is included in the range, whether the upperbound is included.
    """

    logging.debug(f"checking if string \"{r}\" is an interval")
    m = re.match(r"^\s*(?P<lincluded>[\(\)\[\]])\s*(?P<lb>[\+\-]?\d+(?:.\d+)?)\s*,\s*(?P<ub>[\+\-]?\d+(?:.\d+)?)\s*(?P<uincluded>[\(\)\[\]])\s*$", r)
    if m is None:
        raise ValueError(f"the value \"{r}\" does not represent a valid interval!")
    lb_included = m.group("lincluded")
    lb = m.group("lb")
    ub = m.group("ub")
    ub_included = m.group("uincluded")

    lb_included = True if lb_included in r"[)" else False
    ub_included = True if ub_included in r"](" else False
    lb = float(lb)
    ub = float(ub)

    return lb, ub, lb_included, ub_included


def convert_multiline_string_in_command(s: str) -> str:
    """
    Convert a string which should represent a bash command with python multiline string
    in a string actually representing the command
    :param s: the string to convert
    :return:
    """
    return re.sub(r"[ \t\n]+", " ", s).strip(" ")


def convert_str_to_bool(s: str) -> bool:
    """
    Convert a string to a boolean
    :param s: either "true" or "false", case insensitive
    :return:
    """
    if s.lower() == "true":
        return True
    elif s.lower() == "false":
        return False
    else:
        raise ValueError(f"can't convert to bool {s}!")


def convert_range_into_int(r: str) -> Tuple[int, int, bool, bool]:
    m = re.match(r"(?P<open>\[|\]|\()\s*(?P<lowerbound>\d+)\s*;\s*(?P<upperbound>\d+)\s*(?P<close>\]|\[|\))", r)
    if m is None:
        raise ValueError("can't decode string {}".format(r))
    open = m.group("open")
    lowerbound = m.group("lowerbound")
    upperbound = m.group("upperbound")
    close = m.group("close")

    if open in "[":
        bopen = True
    elif open in "(]":
        bopen = False
    else:
        raise ValueError("can't decode open")

    if close in "]":
        bclose = True
    elif close in "[)":
        bclose = False
    else:
        raise ValueError("can't decode close")

    return int(lowerbound), int(upperbound), bopen, bclose


def percentage_to_number(perc: str) -> float:
    if perc.endswith("%"):
        return float(perc[:-1])
    return float(perc)


def convert_int_list_into_str(l: List[int]) -> str:
    """

    :param l: a list of integer e.g. [1,2,3]
    :return: the string converted without whitespaced e.g., [1,2,3]
    """
    return "["+','.join(map(str, l))+"]"


def convert_named_dict_to_alias_dict(d: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
    return {k: d[aliases[k]] for k in d}


class AbstractCsvReader(abc.ABC):

    def __init__(self, csv_filename: str):
        self._csv_filename = csv_filename
        self.header = []

    def __enter__(self):
        self._csv_file = open(self._csv_filename, 'r')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._csv_file.close()
        pass

    @abc.abstractmethod
    def handle_separation(self, i: int, line: str) -> str:
        pass

    @abc.abstractmethod
    def handle_header(self, i: int, line: List[str], sep: str):
        pass

    @abc.abstractmethod
    def handle_legit_line(self, i: int, line: List[str], sep: str) -> Any:
        """

        :param line:
        :param sep:
        :return: stuff to yield to the caller
        """
        pass

    def __iter__(self):
        is_next_header = True
        sep = ","
        for i, line in enumerate(self._csv_file):
            if line.startswith('sep='):
                sep = self.handle_separation(i, line)
            else:
                line = line.rstrip().split(sep)

                if is_next_header:
                    # reading header
                    self.handle_header(i, line, sep)
                    is_next_header = False
                else:
                    # reading line
                    result = self.handle_legit_line(i, line, sep)
                    yield result


class UnknownCsvReader(AbstractCsvReader):

    def __init__(self, csv_filename: str, ):
        AbstractCsvReader.__init__(self, csv_filename)
        self.header = []

    def handle_separation(self, i: int, line: str) -> str:
        pass

    def handle_header(self, i: int, line: List[str], sep: str):
        self.header = line

    def handle_legit_line(self, i: int, line: List[str], sep: str) -> Any:
        result = {}
        for j, h in enumerate(self.header):
            result[h] = line[j]
        return result


class CsvReader(AbstractCsvReader):
    """
    Utility class used to read a csv file using an iterator.
    This allows to use few memory

    Csv internals:
     ID,VALUE,DESCRIPTION
     0,3,hello
     1,6,world
     2,9,foo

    with CsvReader("example.csv", int, int, str) as f:
        for id, value, description in f:
            # do something with the values

    """

    def __init__(self, csv_filename: str, types: List[type], delimiter=','):
        AbstractCsvReader.__init__(self, csv_filename)
        self._delimiter = delimiter
        self.header = []
        self._types = types

    def handle_separation(self, i: int, line: str) -> str:
        self._delimiter = line.split('=')[1]

    def handle_header(self, i: int, line: List[str], sep: str):
        self.header = line

    def handle_legit_line(self, i: int, line: List[str], sep: str) -> Any:
        # reading line
        result = []
        for j, column in enumerate(line):
            # automatic casting
            try:
                if self._types[j] == bool:
                    if column in ['True', 'true']:
                        value = True
                    elif column in ['False', 'false']:
                        value = False
                    else:
                        raise ValueError(f"cannot convert {column} in boolean!")
                else:
                    value = self._types[j](column)

                result.append(value)
            except IndexError:
                pass
        return result


# class KS001:
#     """
#     A convention used to name output file such that you can easily tell what was the configurqation used to create the
#     file.
#
#     The convention split the file name in different sections, separated by what is called "dict_separator". Each section
#     represents a map (a dictionary) of key-values pair. Keys are always string while values can ber whatever they want
#     (given that they are serializable in strings of course). Each key-value pair is separated by a "pair separator" while
#     the key is seaprated form the value with a "key value separator".
#
#     If a key has a null value, the key won't be present at all in the filename.
#     For example if the configuration was:
#
#     a=5, b=3, c="hello"
#
#     the filename generated will be;
#
#     a=5_b=3_c=hello
#
#     The name convention is called KS001.
#     The specification where we decide the separators as well (by default |,_,=) i called KS002.
#     """
#
#     def __init__(self):
#         self.dicts: List[Dict[str, Any]] = []
#
#     def __check_dict(self, i: int):
#         if i < 0:
#             i = -i - 1
#
#         while len(self.dicts) <= i:
#             self.dicts.append({})
#
#     def add(self, i: int = None, k: str = None, v: Any = None, dict: Dict[str, Any] = None) -> "KS001":
#         if dict is not None and v is not None:
#             raise ValueError(f"option v and dict can't be simultaneously be present!")
#         if dict is None and v is None:
#             raise ValueError(f"at last one among option v and dict must be present!")
#         if i is None:
#             i = -1  # we update always the latest
#         if dict is not None:
#             self.update_dict(i, dict)
#         if v is not None:
#             self.add_key_value(i, k, v)
#
#         return self
#
#     def add_key_value(self, i: int, k: str, v: Any) -> "KS001":
#         self.__check_dict(i)
#         self.dicts[i][k] = v
#         return self
#
#     def add_key_value_in_head(self, k: str, v: Any) -> "KS001":
#         self.__check_dict(0)
#         self.dicts[0][k] = v
#         return self
#
#     def add_key_value_in_tail(self, k: str, v: Any) -> "KS001":
#         self.__check_dict(-1)
#         self.dicts[-1][k] = v
#         return self
#
#     def update_dict(self, i: int, d: Dict[str, Any]) -> "KS001":
#         self.__check_dict(-1)
#         self.dicts[i].update(d)
#         return self
#
#     def update_latest_dict(self, d: Dict[str, Any]) -> "KS001":
#         self.__check_dict(-1)
#         self.dicts[-1].update(d)
#         return self
#
#     def update_head_dict(self, d: Dict[str, Any]) -> "KS001":
#         self.update_dict(0, d)
#         return self
#
#     def clear(self) -> "KS001":
#         self.dicts.clear()
#         return self
#
#     def has_key_in_dict(self, i: int, k: str) -> bool:
#         return k in self.dicts[i]
#
#     def has_key_value_in_dict(self, i: int, k: str, v: Any) -> bool:
#         return k in self.dicts[i] and self.dicts[i][k] == v
#
#     def has_compliant_dict(self, i: int, dict: Dict[str, Any]) -> bool:
#         """
#         check if the the second dict is compliant with the first one
#
#         this operation is not commutative!
#
#         :param i:
#         :param dict:
#         :return:
#         """
#         for x in self.dicts[i]:
#             if x not in dict.keys():
#                 # a key in the structure does not belong to dict.
#                 # if the value of the key is None in the self it's still correct, optherwise it is not
#                 if self.dicts[i][x] is None:
#                     continue
#                 else:
#                     return False
#             if self.dicts[i][x] != dict[x]:
#                 # the values do not match
#                 return False
#         return True
#
#     def get_value_in_dict(self, i: int, k: str) -> Any:
#         return self.dicts[i][k]
#
#     def __getitem__(self, item: int) -> Dict[str, Any]:
#         return self.dicts[item]
#
#     def __str__(self) -> str:
#         result = []
#         for i, d in enumerate(self.dicts):
#             result.append(str(i) + ": {" + ", ".join(map(lambda k: f"{k}={str(d[k])}", sorted(d.keys()))) + "}")
#         return "\n".join(result)
#
#     def dump(self, aliases: Dict[str, str] = None, dict_split: str = constants.SEPARATOR_DICT, pairs_split: str = constants.SEPARATOR_PAIRS, keyvalue_split: str = constants.SEPARATOR_KEYVALUE) -> str:
#         result = []
#         for d in self.dicts:
#             dict_str = []
#             for k in sorted(d.keys()):
#                 if d[k] is None:
#                     continue
#                 if aliases is not None and k in aliases:
#                     new_key = aliases[k]
#                 else:
#                     new_key = k
#                 dict_str.append(f"{str(new_key)}{keyvalue_split}{str(d[k])}")
#             result.append(pairs_split.join(dict_str))
#         return dict_split.join(result)
#
#     def get_phddictionaries_compliant_from_directory(self, index: int, directory: str,
#                                                      allowed_extensions: Iterable[str], alias_name_dict: Dict[str, str] = None) -> Iterable[Tuple[str, "KS001"]]:
#         for f in os.listdir(directory):
#             # check if extension is compliant
#             if f.split('.')[-1] not in allowed_extensions:
#                 continue
#             filename_no_extension = ".".join(f.split(".")[0:-1])
#             # parse the phd dictionary. This may contain more or less keys of self. If it contains less keys, then they won't be compliant at all!
#             other = KS001.parse(filename_no_extension, conversions=smart_parse_conversions, alias_name_dict=alias_name_dict)
#             if self.has_compliant_dict(i=index, dict=other.dicts[index]):
#                 yield (f, other)
#
#     @classmethod
#     def parse(cls, s: str, conversions: Callable[[int, str, str], Any] = None, alias_name_dict: Dict[str, str] = None, dict_split: str = constants.SEPARATOR_DICT, pairs_split: str = constants.SEPARATOR_PAIRS, keyvalue_split: str = constants.SEPARATOR_KEYVALUE) -> "KS001":
#         """
#         Parse a KS001 and/or KS002 filename string into a dictionary set
#
#         :param s: the string to parse
#         :param conversions: a function which  convert a triple index/key/string into index/key/value. If None we will put the string as value
#         :param alias_name_dict: an optional dictionary that converts aliases in real names
#         :param dict_split: separator of dicts. Defaultys to KS002
#         :param pairs_split: separator of keypairs. Defaults to KS002
#         :param keyvalue_split: separator of keyvalue. Defaults to KS002
#         :return: a list of dictionaries representing the KS001 object
#         """
#         result = cls()
#
#         for i, adict in enumerate(s.split(dict_split)):
#             result.dicts.append({})
#             for j, apair in enumerate(adict.split(pairs_split)):
#                 key = apair.split(keyvalue_split)[0]
#                 value = apair.split(keyvalue_split)[1]
#                 if alias_name_dict is not None:
#                     if key in alias_name_dict:
#                         key = alias_name_dict[key]
#                 if conversions is not None:
#                     value = conversions(i, key, value)
#                 result.dicts[i][key] = value
#         return result


def smart_parse_conversions(index: int, key: str, value: str) -> Any:
    if re.match(r"[+\-]?\d+$", value):
        return int(value)
    if re.match(r"[+\-]?\d+\.\d+", value):
        return float(value)
    try:
        return convert_str_to_bool(value)
    except ValueError:
        return str(value)


def is_number(p: str) -> bool:
    """
    Check if a stirng represents a number
    :param p:
    :return:
    """

    logging.info(f"p is \"{p}\" type({type(p)}")
    return re.match(r"^\d+(?:\.\d+)?$", p) is not None


def is_percentage(p: str) -> bool:
    """
    Check i f a string represents a percentage

    :param p: the string to check
    :return:
    """
    if isinstance(p, str) and p.endswith('%'):
        return True
    else:
        return False


def parse_number(p: str) -> int:
    """

    :param p: a string like "5%" or a string like "5"
    :return: the number(e.g., 5)
    """

    if p.endswith("%"):
        return int(p[0:-1])
    else:
        return int(p)

