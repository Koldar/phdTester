import abc
import textwrap
from decimal import Decimal
from typing import Iterable

from phdTester.plotting.plotting import IAxis, IText, ISinglePlot, ILegend, IGrid, IPlot2DGraph


class IPlotTextFormatter(abc.ABC):

    @abc.abstractmethod
    def format(self, index: int, lower_bound: float, upper_bound: float, value: str) -> str:
        """
        Format a value to be put on a axis tick

        :param index: the index of the tick. For exmaple the first tick, the second tick, the i-th tick
        :param lower_bound: the lowerbound on the beginning of the axis
        :param upper_bound: the upperbound on the end of the axis
        :param value: the value to convert
        :return: a string representation of the value to print on the plot
        """
        pass


class StringPlotTextFormatter(IPlotTextFormatter):

    def format(self, index: int, lower_bound: float, upper_bound: float, value: str) -> str:
        return str(value)


class ExponentialNotationPlotTextFormatter(IPlotTextFormatter):

    def format(self, index: int, lower_bound: float, upper_bound: float, value: str) -> str:
        return '{:.2E}'.format(Decimal(value))


class Visible:

    def __init__(self):
        self.visible = True

    @property
    def visible(self) -> bool:
        return self.visible

    @visible.setter
    def visible(self, value: bool):
        self.visible = value


class DefaultAxis(IAxis):

    @property
    def formatter(self) -> IPlotTextFormatter:
        return self._formatter

    @formatter.setter
    def formatter(self, value: "IPlotTextFormatter"):
        self._formatter = value

    def __init__(self, values: Iterable[float], atype: str, name: str, formatter: "IPlotTextFormatter" = None):
        self._axis = list(values)
        self._min = min(self._axis)
        self._max = max(self._axis)
        self._type = atype
        self._label = DefaultText(name)
        self._cumulative = False
        self._log2 = False
        self._formatter = formatter or StringPlotTextFormatter()

    def __iter__(self) -> Iterable[float]:
        return iter(self._axis)

    @property
    def min(self) -> float:
        return self._min

    @property
    def max(self) -> float:
        return self._max

    @property
    def axis_type(self) -> str:
        return self._type

    @property
    def label(self) -> "IText":
        return self._label

    @property
    def cumulative(self) -> bool:
        return self._cumulative

    @cumulative.setter
    def cumulative(self, value: bool):
        self._cumulative = value

    @property
    def log2(self) -> bool:
        return self._log2

    @log2.setter
    def log10(self, value: bool):
        self._log2 = value

    def __len__(self) -> int:
        return len(self._axis)


class DefaultSinglePlot(ISinglePlot):

    def __init__(self, values: Iterable[float], name: str):
        ISinglePlot.__init__(self)
        self._values = list(values)
        self._label = DefaultText(name)

    def __iter__(self) -> Iterable[float]:
        return iter(self._values)

    def __getitem__(self, item) -> float:
        return self._values[item]

    @property
    def label(self) -> "IText":
        return self._label

    def __len__(self) -> int:
        return len(self._values)


class DefaultText(IText):

    def __init__(self, t: str, font_size: int = 16, wrap_up_to: int = -1):
        """
        initialize a new text label
        :param t: the text
        :param font_size: the size fo the font
        :param wrap_up_to: the maximum width of the text If it's more it is automatically carriaged return
            put a negative number to disable this behaviour
        """
        IText.__init__(self)
        self._text = t
        self._font_size = font_size
        self._wrap_up_to = wrap_up_to

    @property
    def wrap_up_to(self) -> int:
        return self._wrap_up_to

    @wrap_up_to.setter
    def wrap_up_to(self, value: int):
        self._wrap_up_to = value

    @property
    def text(self) -> str:
        if self._wrap_up_to <= 0:
            return self._text
        return "\n".join(textwrap.wrap(self._text, width=self._wrap_up_to))

    @text.setter
    def text(self, value: str):
        self._text = value

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int):
        self._font_size = value


class DefaultLegend(ILegend):

    def __init__(self, plot2dgraph: "IPlot2DGraph"):
        ILegend.__init__(self)
        self._plot2dgraph = plot2dgraph

    @property
    def plot2DGraph(self) -> "IPlot2DGraph":
        return self._plot2dgraph


class DefaultGrid(IGrid):

    def __init__(self):
        IGrid.__init__(self)

