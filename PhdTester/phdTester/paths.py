import abc
import os
from typing import Union, Iterable

from phdTester.ks001.ks001 import KS001


class ImportantPaths(abc.ABC):
    """
    This class represents an object allowing you not to worry about absolute paths at all

    You can use the methods in this function to generate filenames inside the output folder of your project
    """

    def __init__(self, input_dir: str, output_dir: str, tmp_subdir: str, csv_subdir: str, image_subdir: str, cwd_subdir: str):
        """

        :param input_dir: a directory that will be used to fetch data from
        :param output_dir:a directory containing all the files generated by this run of the Phd Tester
        :param tmp_subdir: name of a subdirectory of output representing a folder where to put temporary data
        :param csv_subdir: name of a subdirectory of output representing a folder where to put all the experiments csv
        :param image_subdir: name of a subdirectory of output representing a folder where to put all the interesting images
        :param cwd_subdir: name of a subdirectory of output representing a folder where to execute external commands (if any)
        """
        self._input_dir = os.path.abspath(input_dir)
        self._output_dir = os.path.abspath(output_dir)
        self._tmp_dir = tmp_subdir
        self._csv_dir = csv_subdir
        self._image_dir = image_subdir
        self._cwd_dir = cwd_subdir

    def get_input(self, *p: str) -> str:
        """

        :param p: list of string representing a subpath relative to the input folder.
        :return: absolute path of a file within a folder called "input" representing a read-only folder
        """
        return os.path.abspath(os.path.join(self._input_dir, *p))

    def get_output(self, *p: str) -> str:
        """

        :param p: list fo string representing the paths of a file inside the output directory
        :return: absolute path of a file relative to the output directory
        """
        return os.path.abspath(os.path.join(self._output_dir, *p))

    def get_tmp(self, *p: str) -> str:
        """

        :param p: list fo string representing the paths of a file inside the tmp directory
        :return: absolute path of a file relative to the tmp directory
        """
        return os.path.abspath(os.path.join(self.get_tmp_dir(), *p))

    def get_csv(self, *p: str) -> str:
        """

        :param p: list of string representing the paths of a file inside the csv directory
        :return: absolute path of a file relative to the csv directory
        """
        return os.path.abspath(os.path.join(self.get_csv_dir(), *p))

    def get_cwd(self, *p: str) -> str:
        """

        :param p: list of string representing the paths of a file inside the cwd directory
        :return: absolute path of a file relative to the cwd directory
        """
        return os.path.abspath(os.path.join(self.get_cwd_dir(), *p))

    def get_image(self, *p: str) -> str:
        """

        :param p: list of string representing the paths of a file inside the image directory
        :return: absolute path of a file relative to the image directory
        """
        return os.path.abspath(os.path.join(self.get_image_dir(), *p))

    def get_input_dir(self) -> str:
        """

        :return: the absolute path of the directory where all program input is located
        """
        return os.path.abspath(self._input_dir)

    def get_output_dir(self) -> str:
        """

        :return: the absolute path of the directory where all program output is located
        """
        return os.path.abspath(self._output_dir)

    def get_csv_subdir(self) -> str:
        return self._csv_dir

    def get_tmp_subdir(self) -> str:
        return self._tmp_dir

    def get_cwd_subdir(self) -> str:
        return self._cwd_dir

    def get_image_subdir(self) -> str:
        return self._image_dir

    def get_csv_dir(self) -> str:
        """

        :return: the absolute path of the directory where we should look for csvs
        """
        return os.path.abspath(os.path.join(self._output_dir, self._csv_dir))

    def get_tmp_dir(self) -> str:
        """

        :return: the absolute path of the directory where all program temporary data is located
        """
        return os.path.abspath(os.path.join(self._output_dir, self._tmp_dir))

    def get_image_dir(self) -> str:
        """

        :return: the absolute path of the directory where all program images are stored
        """
        return os.path.abspath(os.path.join(self._output_dir, self._image_dir))

    def get_cwd_dir(self) -> str:
        """

        :return: the absolute path of the directory where all program extenral programs should be called
        """
        return os.path.abspath(os.path.join(self._output_dir, self._cwd_dir))

    def _generate_file(self, ks: "KS001", extension: str = None, prepath: str = os.pardir, p: Union[str, Iterable[str]] = None, colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> str:
        """
        Generate the absolute path of a filename compliant with KS001 standard

        This function does **not** create an actual file, but it just generate the filename

        :param ks: the structure to dump
        :param extension: the extension of the filename to generate. If you leave the extension to None,
            the filename generated won't have any extension
        :param prepath a path to put between the output directory and the given path `p`
        :param p: a list of string each representing the subfolder in a directory or a single string representing
            the subpath
        :return: the string representing the filename generated contained in the output folder
        """

        if extension is not None:
            extension = "." + extension
        else:
            extension = ""
        if p is None:
            p = list(os.pardir)
        elif isinstance(p, str):
            p = [p]
        elif isinstance(p, list):
            pass
        else:
            raise TypeError(f"p {p} can only be string or iterable of string")
        final = os.path.abspath(os.path.join(self.get_output_dir(), prepath, *p))
        return self.get_output(final, ks.dump_str(
            use_key_alias=True,
            use_value_alias=True,
            colon=colon,
            pipe=pipe,
            underscore=underscore,
            equal=equal,
        ) + extension)

    def generate_image_file(self, ks: "KS001", p: Union[str, Iterable[str]] = None, extension: str = None) -> str:
        """
        generates a filename which is inside the "image" folder

        :param ks: the ks representing the filename to generate
        :param p: optional subdirectories in "image" folder
        :param extension: the extension of the file to generate
        :return: absolute path of the filename generated
        """
        return self._generate_file(ks, prepath=self.get_image_subdir(), extension=extension, p=p)

    def generate_csv_file(self, ks: "KS001", p: Union[str, Iterable[str]] = None, extension: str = None) -> str:
        return self._generate_file(ks, prepath=self.get_csv_subdir(), extension=extension, p=p)

    def generate_cwd_file(self, ks: "KS001", p: Union[str, Iterable[str]] = None, extension: str = None) -> str:
        return self._generate_file(ks, prepath=self.get_cwd_subdir(), extension=extension, p=p)

    def generate_output_file(self, ks: "KS001", p: Union[str, Iterable[str]] = None, extension: str = None) -> str:
        return self._generate_file(ks, prepath=os.pardir, extension=extension, p=p)

