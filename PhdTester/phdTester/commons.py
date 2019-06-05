import abc
import cProfile
import inspect
import io
import logging
import math
import multiprocessing
import os
import pstats
import re
import shutil
import subprocess
from io import StringIO
from multiprocessing import Process
from typing import Any, Iterable, Callable, Union, Dict, Tuple, List

import pandas
import string_utils


class SlottedClass(object):

    __slots__ = ()


def sequential_numbers(int_stream: Iterable[float], interval: float = 1.0) -> Tuple[float, float]:
    """
    Generate a sequence of ranges starting from a sequence

    for example
    ```
    1 2 3 4 7 8 9 10 11 12 15
    ```
    will generate
    ```
    (1,4) (7,12), (15, 15)
    ```

    :param int_stream: the stream to compress
    :param interval: the difference between the current number and the previous one that we need to check
        to understand when a sequence "breaks"
    :return:
    """
    start = None
    previous = None
    for i in int_stream:
        if start is None:
            # we need to start a new sequence
            start = i
            previous = i
        elif math.isclose(i, (previous + interval)):
            # we're continuing a contiguous sequence of numbers
            previous = i
        else:
            # we're breaking a sequence of numbers
            yield (start, previous)
            start = i
            previous = i

    # when we have finished we might need to close the last sequence of numbers
    yield (start, i)


def generate_aliases(strings: List[str]) -> Dict[str, str]:
    """
    generate a set of aliases from the given set of strings.



    :param strings:
    :return:
    """
    result = {}
    for option in strings:
        if string_utils.is_camel_case(option):
            # fetch the first an all the uppercase characters to generate the alias
            alias: str = option[0] + ''.join(filter(lambda x: x.isupper(), option))
        elif string_utils.is_snake_case(option, "_"):
            # TODO implement
            raise NotImplementedError()
        elif option.islower() and re.match(r"^[a-z0-9]+$", option):
            # ok maybe it's camel case of snake case but it contains only one word (e.g., run), HENCE
            # we need to handle words like "algorithm" or "run" which are special case
            # of camel case (they do not have upper letters)
            alias: str = option.lower()[0]
        else:
            raise ValueError(f"option \"{option}\" is not neither camelcase nor snakecase!")
        alias = alias.lower()
        result[option] = alias
    return result


def time_profile(sort: List[str], limit: int = None):
    """

    :param sort: sort the outcome according to a statistic. Allowed values are:
     - name: sort over the function name
     - cumulative: sort over the functions which took more time during all its calls.
     - time: sort over the function which took more time per call
    :param limit:
    :return:
    """

    def decorator(func):
        pr = cProfile.Profile()

        def wrapped(*args, **kwargs):
            pr.enable()
            func(*args, **kwargs)
            pr.disable()

            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats(*sort)
            ps.print_stats(limit)
            print(s.getvalue())

        return wrapped

    return decorator


def expand_string(string: str, to_replace: List[Tuple[str, str]]) -> str:
    """
    Within string replace a character in the first value of a pair to the second value of a pair.
    If the string contains the character in the second value, the character will be doubled.

    :param string:
    :param to_replace: the mapping between character to replace and what are the substitutes. Mapping
    must be unique. The mapping ordered **is important**.

    :return: the string replaced
    """

    # keys must be unique
    if len(set(map(lambda x: x[0], to_replace))) < len(to_replace):
        raise ValueError(f"2 keys are the same!")
    # vlaues must be uniqye
    if len(set(map(lambda x: x[1], to_replace))) < len(to_replace):
        raise ValueError(f"2 values are the same!")

    # clean the string from any replacement character
    for i, (_, replacement) in enumerate(to_replace):
        if replacement in string:
            # replacement will be "XX" or "XXX" or "XXXX" but we endure it will never be "X"
            string = string.replace(replacement, replacement * (i+2))

    # ok, now we're sure that string does not contain single replacement characters
    for i, (to_replace_char, replacement) in enumerate(to_replace):
        if re.search(to_replace_char * 2, string) is not None:
            raise ValueError(f"value to replace {to_replace} is present twice contigouosly in string {string}!")
        if to_replace_char in string:
            string = string.replace(to_replace_char, replacement)

    return string


def dexpand_string(string: str, to_replace: List[Tuple[str, str]]) -> str:
    """
    inverse operation of expand_string

    :param string: output of expand_string
    :param to_replace: the same variable passed to expand_string
    :return:
    """

    # keys must be unique
    if len(set(map(lambda x: x[0], to_replace))) < len(to_replace):
        raise ValueError(f"2 keys are the same!")
    # vlaues must be uniqye
    if len(set(map(lambda x: x[1], to_replace))) < len(to_replace):
        raise ValueError(f"2 values are the same!")

    for i, (to_replace, replacement) in enumerate(to_replace):
        # perform the replacement -> to_replace
        string = re.sub("[^" + replacement + "]?" + replacement + "[^" + replacement + "]?", to_replace, string)

    for i, (to_replace, replacement) in enumerate(to_replace):
        # replace "XXX" to single "X"
        string = re.sub(replacement * i, replacement, string)

    return string


def get_ks001_extension(filename: str, pipe: str = "|") -> str:
    """
    get extension of filename

    filename extension is the string going from the end till the last dictionary separator.

    For example |a=5_b=2|.csv will return "csv"
    For example |a=5_b=2|.original.csv will return "original.csv"
    For example |a=5_b=2|csv will lead to UB

    :param filename: the filename to check. Implicitly under KS001 format
    :param pipe: the character used by KS001 to divide dictionaries
    :return: the extension. May contain multiple "."
    """

    return filename[filename.rfind(pipe)+2:]


def get_ks001_basename_no_extension(filename: str, pipe: str = "|") -> str:
    filename = os.path.basename(filename)
    return filename[0: filename.rfind(pipe)+1]


def convert_pandas_csv_row_in_dict(pandas_csv) -> Dict[str, Any]:
    """
    Convert a row of a csv read with `pandas.read_csv` into a dictionary

    :param pandas_csv: the row to convert
    :return: a dictionary
    """
    return pandas_csv.to_dict('records')[0]


def convert_pandas_data_frame_in_dict(panda_dataframe: pandas.DataFrame) -> Dict[str, List[float]]:
    d = panda_dataframe.to_dict('series')
    return {k: list(d[k]) for k in d}


def get_filenames_in_paths(afrom: str, allowed_extensions: Iterable[str] = None) -> Iterable[Tuple[str, str]]:
    for abs_path in get_filenames(afrom, allowed_extensions=allowed_extensions):
        yield (abs_path, get_ks001_extension(abs_path))


def remove_filenames_in_path(afrom: str, allowed_extensions: Iterable[str] = None):
    """
    Remove all the filenames in the directory having as extension the given ones

    :param afrom: the directory where we need to remove files from
    :param allowed_extensions: the extension of the files we need to remove
    :return:
    """
    for abs_path in get_filenames(afrom, allowed_extensions=allowed_extensions):
        try:
            os.remove(abs_path)
        except OSError:
            pass


def move_filenames_to(afrom: str, ato: str, allowed_extensions: Iterable[str] = None) -> Iterable[str]:
    """
    Move all the file which can be found in `afrom` to `ato` directory.
    :param afrom: the directory where to look for files
    :param ato: the directory where to move the files to
    :param allowed_extensions: if present we will move **all** the files which have these extensions
    :return: the list of absolute paths just moved
    """
    result = []
    for abs_path in get_filenames(afrom, allowed_extensions=allowed_extensions):
        to_abs_path = os.path.relpath(abs_path, afrom)
        logging.debug(f"relpath is {to_abs_path}")
        new_path = os.path.abspath(os.path.join(ato, to_abs_path))
        logging.debug(f"new abs path us {to_abs_path}")
        shutil.move(abs_path, new_path)
        result.append(new_path)
    return result


def get_filenames(directory: str, allowed_extensions: Iterable[str] = None) -> Iterable[str]:
    """
    get all the absolute paths of the filenames inside the gtiven directory

    :param directory: the directory where to look for
    :param allowed_extensions: the externsion we care aboud. File not having the given extension will be ignored
    :return: list of absolute paths representing the interesting filenames
    """

    for f in os.listdir(directory):
        # check if extension is compliant
        if allowed_extensions is not None and f.split('.')[-1] not in allowed_extensions:
            continue
        yield os.path.abspath(os.path.join(directory, f))


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


def get_file_extension(f: str) -> str:
    return f.split('.')[-1]


def list_with_extension(path: str, extension: str) -> List[str]:
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and get_file_extension(f) == extension]


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
    safe_dict['map'] = map
    safe_dict['list_with_extension'] = list_with_extension
    safe_dict['sorted'] = sorted

    logging.info(f"""string we're going to evaluate is \n{s}""")
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

    def __init__(self):
        self.header = []

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abc.abstractmethod
    def line_iterator(self) -> Iterable[str]:
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
        for i, line in enumerate(self.line_iterator()):
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


class AbstractFileCsvReader(AbstractCsvReader, abc.ABC):

    def __init__(self, csv_filename: str):
        AbstractCsvReader.__init__(self)
        self._csv_filename = csv_filename
        self.header = []

    def __enter__(self):
        self._csv_file = open(self._csv_filename, 'r')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._csv_file.close()
        pass

    def line_iterator(self) -> Iterable[str]:
        return self._csv_file


class UnknownStringCsvReader(AbstractCsvReader):

    def __init__(self, it: Iterable[str]):
        AbstractCsvReader.__init__(self)
        self.it = it

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def line_iterator(self) -> Iterable[str]:
        return self.it

    def handle_separation(self, i: int, line: str) -> str:
        pass

    def handle_header(self, i: int, line: List[str], sep: str):
        self.header = line

    def handle_legit_line(self, i: int, line: List[str], sep: str) -> Any:
        result = {}
        for j, h in enumerate(self.header):
            result[h] = line[j]
        return result


class UnknownCsvReader(AbstractFileCsvReader):

    def __init__(self, csv_filename: str):
        AbstractFileCsvReader.__init__(self, csv_filename=csv_filename)
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


class CsvReader(AbstractFileCsvReader):
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
        AbstractFileCsvReader.__init__(self, csv_filename=csv_filename)
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


class AbstractCsvWriter(abc.ABC):

    def __init__(self, separator: str):
        self.separator_handled = False
        self.header_handled = False
        self._row = 0
        self.separator = separator

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abc.abstractmethod
    def _write_separator(self):
        pass

    @abc.abstractmethod
    def _write_header(self):
        pass

    @abc.abstractmethod
    def _write_row(self, i: int, row: List[str]):
        pass

    def write(self, row: Union[str, List[Any]]):
        if not self.separator_handled:
            self._write_separator()
            self.separator_handled = True
        if not self.header_handled:
            self._write_header()
            self.header_handled = True

        if isinstance(row, str):
            row = list(row.split(self.separator))
        elif isinstance(row, list):
            row = list(map(str, row))
        else:
            raise TypeError(f"row must be either a string or a list")
        self._write_row(self._row, row)
        self._row += 1


class StringCsvWriter(AbstractCsvWriter):

    def __init__(self, separator: str, header: List[str]):
        super().__init__(separator=separator)
        self.header = header
        self._csv = StringIO()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _write_separator(self):
        pass

    def _write_header(self):
        self._csv.write(self.separator.join(self.header) + "\n")

    def _write_row(self, i: int, row: List[str]):
        self._csv.write(self.separator.join(row) + "\n")

    def get_string(self) -> str:
        return self._csv.getvalue()


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

