import abc
import logging
import math
import os
from typing import Iterable, Tuple, Optional, Any, Union

from phdTester.ks001.ks001 import KS001


class Visible:

    def __init__(self):
        self._visible = True

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value


class IAxis(abc.ABC):

    @abc.abstractmethod
    def __iter__(self) -> Iterable[float]:
        pass

    @property
    @abc.abstractmethod
    def axis_type(self) -> str:
        pass

    @property
    def axis(self) -> Iterable[float]:
        return iter(self)

    @property
    @abc.abstractmethod
    def min(self) -> float:
        pass

    @property
    @abc.abstractmethod
    def max(self) -> float:
        pass

    @property
    @abc.abstractmethod
    def label(self) -> "IText":
        pass

    @property
    @abc.abstractmethod
    def cumulative(self) -> bool:
        pass

    @cumulative.setter
    @abc.abstractmethod
    def cumulative(self, value: bool):
        pass

    @property
    def linear(self) -> bool:
        return not self.cumulative

    @linear.setter
    def linear(self, value: bool):
        self.cumulative = not value

    @property
    @abc.abstractmethod
    def log10(self) -> bool:
        pass

    @log10.setter
    @abc.abstractmethod
    def log10(self, value: bool):
        pass

    @property
    def identity(self) -> bool:
        return not self.log10

    @identity.setter
    def identity(self, value: bool):
        self.log10 = not value

    @property
    @abc.abstractmethod
    def formatter(self) -> "IPlotTextFormatter":
        pass

    @formatter.setter
    @abc.abstractmethod
    def formatter(self, value: "IPlotTextFormatter"):
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        pass


class ISinglePlot(abc.ABC):

    @abc.abstractmethod
    def __iter__(self) -> Iterable[float]:
        pass

    @abc.abstractmethod
    def __getitem__(self, item: int) -> Tuple[float, str]:
        pass

    @abc.abstractmethod
    def values_and_labels(self) -> Iterable[Tuple[float, Optional[str]]]:
        pass

    @abc.abstractmethod
    def has_some_labels(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def label(self) -> "IText":
        pass

    @abc.abstractmethod
    def __len__(self) -> int:
        pass


class IText(abc.ABC, Visible):

    def __init__(self):
        Visible.__init__(self)

    @property
    @abc.abstractmethod
    def text(self) -> str:
        pass

    @text.setter
    @abc.abstractmethod
    def text(self, value: str):
        pass

    @property
    @abc.abstractmethod
    def wrap_up_to(self) -> int:
        pass

    @wrap_up_to.setter
    @abc.abstractmethod
    def wrap_up_to(self, value: int):
        pass

    @property
    @abc.abstractmethod
    def font_size(self) -> int:
        pass

    @font_size.setter
    @abc.abstractmethod
    def font_size(self, value: int):
        pass


class ILegend(abc.ABC, Visible):

    def __init__(self):
        Visible.__init__(self)

    @property
    @abc.abstractmethod
    def plot2DGraph(self) -> "IPlot2DGraph":
        pass


class IGrid(abc.ABC, Visible):

    def __init__(self):
        Visible.__init__(self)


class IPlot2DGraph(abc.ABC):

    @abc.abstractmethod
    def add_plot(self, yaxis: ISinglePlot):
        pass

    @abc.abstractmethod
    def get_plots(self, name: str) -> ISinglePlot:
        pass

    @abc.abstractmethod
    def contains_plot(self, name: str) -> bool:
        pass

    @abc.abstractmethod
    def plots(self) -> Iterable[ISinglePlot]:
        pass

    @abc.abstractmethod
    def plots_map(self) -> Iterable[Tuple[IAxis, ISinglePlot]]:
        pass

    @abc.abstractmethod
    def save_image(self, image_filename_no_extension: Union[str, KS001], save_raw_data: bool, folder: str = None) -> Any:
        """
        Generate the plot and saves it in the filesystem

        ::note
        this operation is time consuming

        :param image_filename_no_extension: a structure representing the basename of the image to generate.
            If it's a string we will use it as a basename to generate image related files. If it's a KS001
            object we will use its dump
        :param folder: the folder where we're going to save the image. The option is used only if
            `image_filename_no_extension` is a relative path or when it is actually a KS001 object. Otherwise
            it is ignored.
        :param save_raw_data: if true we will create a CSV in the same directory of the image containing the data
        related to the image. The name will be the same of the image associated but the extension will be csv.
        :return:
        """
        pass

    @property
    @abc.abstractmethod
    def title(self) -> "IText":
        pass

    @property
    @abc.abstractmethod
    def xaxis(self) -> "IAxis":
        pass

    @property
    @abc.abstractmethod
    def yaxis(self) -> "IAxis":
        pass

    @property
    @abc.abstractmethod
    def subtitle(self) -> Optional["IText"]:
        pass

    @property
    @abc.abstractmethod
    def legend(self) -> "ILegend":
        pass

    @property
    @abc.abstractmethod
    def grid(self) -> "IGrid":
        pass

    def _save_raw_data(self, csv_filename_no_extension: str):
        csv_filename = f"{csv_filename_no_extension}.csv"
        try:
            os.remove(csv_filename)
        except OSError:
            pass

        with open(csv_filename, "w") as f:
            f.write("LABEL,X,Y\n")
            for i, x in enumerate(self.xaxis):

                old_values = {}
                for j, p in enumerate(self.plots()):
                    try:
                        if self.xaxis.linear:
                            xvalue = x
                        else:
                            if p.label.text not in old_values:
                                old_values[p.label.text] = 0
                            xvalue = old_values[p.label.text] + x

                        if self.yaxis.identity:
                            yvalue = p[i]
                        else:
                            yvalue = math.log10(p[i])

                        f.write(f"{p.label.text},{xvalue},{yvalue}\n")
                    except ValueError:
                        logging.debug(f"skip value {x};{p[i]}: possible because of log?")
