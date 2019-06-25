import itertools
import logging
import os
from typing import Iterable, Tuple, Optional, Any, Union, List

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import Formatter

from phdTester import DataTypeStr, KS001Str
from phdTester.ks001.ks001 import KS001
from phdTester.plotting.common import DefaultLegend, DefaultGrid, DefaultText, IPlotTextFormatter
from phdTester.plotting.plotting import IPlot2DGraph, IAxis, ISinglePlot, IText, ILegend, IGrid


class MatPlotCompliantFormatter(Formatter):

    def __call__(self, x, pos=None):
        return self._formatter.format(pos, float("-inf"), float("+inf"), x)

    def __init__(self, formatter: "IPlotTextFormatter"):
        Formatter.__init__(self)
        self._formatter = formatter


class FourMatplotLibPlot2DGraph(IPlot2DGraph):

    @property
    def title(self) -> "IText":
        return self._title

    @property
    def xaxis(self) -> "IAxis":
        return self._xaxis

    @property
    def yaxis(self) -> "IAxis":
        return self._yaxis

    @property
    def subtitle(self) -> Optional["IText"]:
        return self._subtitle

    @property
    def legend(self) -> "ILegend":
        return self._legend

    @property
    def grid(self) -> "IGrid":
        return self._grid

    def __init__(self, xaxis: IAxis, yaxis: IAxis, title: IText, subtitle: IText, create_subfigure_images: bool = True, dictonary_to_add_information: Union[int, str] = None):
        """

        :param xaxis: x axis
        :param yaxis: y axis
        :param title: title of the image
        :param subtitle: subtitle of the image
        :param create_subfigure_images: If true, we will create 4 files representing the single plots in the 4 layout
            figures. Note also that if you choose to generate the csv data, we will generate a csv for each of those 4
            plots.
        :param dictonary_to_add_information: if we decide to save an image from a ks001, this function tells in which
            dictionary we need to add the image information. Ignored if we use a string when calling save_image.
            The value can either be a string (representing the label of the dictionary) or a integer (representing the
            index of the dicitonary to choose)
        """
        self._title = title
        self._subtitle = subtitle
        self._xaxis = xaxis
        self._yaxis = yaxis
        self._legend = DefaultLegend(plot2dgraph=self)
        self._grid = DefaultGrid()
        self._plots = []
        self._create_subfigure_images = create_subfigure_images
        self._dictonary_to_add_information = dictonary_to_add_information

    def add_plot(self, values: ISinglePlot):
        if self.contains_plot(values.label.text):
            raise ValueError(f"singleplot {values.label} is already present in the plot")
        self._plots.append(values)

    def get_plots(self, name: str) -> ISinglePlot:
        return list(filter(lambda p: p.label == name, self.plots()))[0]

    def contains_plot(self, name: str) -> bool:
        return len(list(filter(lambda p: p.label == name, self.plots()))) > 0

    def plots(self) -> Iterable[ISinglePlot]:
        return self._plots

    def plots_map(self) -> Iterable[Tuple[IAxis, ISinglePlot]]:
        return {p.label: p for p in self._plots}

    def save_image(self, image_name: KS001, save_raw_data: bool, folder: str = None, colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> Any:
        """

        :param image_filename_no_extension:
        :param folder:
        :param save_raw_data: True if you want to save the data of the subplots. To do something, you are required
        to save the subplots as well!
        :return:
        """

        multi_image = image_name.clone()
        multi_image.add_key_value(place=self._dictonary_to_add_information, key="mode", value="multi")

        # Create 2x2 sub plots
        mat_gs = gridspec.GridSpec(2, 2)
        mat_fig = plt.figure()

        if self.subtitle is not None:
            real_title = f"{self.title.text}\n{self.subtitle.text}"
        else:
            real_title = f"{self.title.text}"

        total_plots = len(self._plots)
        legend_columns = 3
        legend_rows = np.math.ceil(total_plots / legend_columns)
        ydelta_per_row = 0.05
        title_y = 1 + legend_rows * ydelta_per_row  # each row gives 0.05 of highness

        mat_fig.suptitle(real_title, y=title_y)

        mat_ax1 = mat_fig.add_subplot(mat_gs[0, 0])  # row 0, col 0
        mat_ax2 = mat_fig.add_subplot(mat_gs[0, 1])  # row 0, col 1
        mat_ax3 = mat_fig.add_subplot(mat_gs[1, 0])
        mat_ax4 = mat_fig.add_subplot(mat_gs[1, 1])
        mat_axs = [mat_ax1, mat_ax2, mat_ax3, mat_ax4]

        mat_fig.tight_layout(pad=2, w_pad=2, h_pad=2)
        mat_fig.subplots_adjust(top=0.88)
        # fig.subplots_adjust(top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.25, wspace=0.35)

        xaxis_base = self.xaxis.label.text
        yaxis_base = self.yaxis.label.text

        for i, (cumornot, logornot) in enumerate(itertools.product([False, True], [False, True])):
            xperks = []
            yperks = []
            sub_image: KS001 = multi_image.clone()

            if cumornot:
                xperks.append('cumulative')
            else:
                xperks.append('linear')

            if logornot:
                yperks.append('log10')
            else:
                yperks.append('identity')

            sub_image.add_key_value(place=self._dictonary_to_add_information, key="cumulativex", value=cumornot)
            sub_image.add_key_value(place=self._dictonary_to_add_information, key="logy", value=logornot)

            self.xaxis.cumulative = cumornot
            self.xaxis.log10 = False
            self.xaxis.label.text = "{} ({})".format(xaxis_base, ','.join(xperks))

            self.yaxis.cumulative = False
            self.yaxis.log10 = logornot
            self.yaxis.label.text = "{} ({})".format(yaxis_base, ','.join(yperks))

            plot_figure = MatplotLibPlot2DGraph(
                xaxis=self.xaxis,
                yaxis=self.yaxis,
                title=DefaultText(""),
                subtitle=None,
                use_provided_fig=mat_axs[i]
            )
            plot_figure.legend.visible = False

            for p in self.plots():
                plot_figure.add_plot(p)

            labels, lines = plot_figure.save_image(
                image_name=sub_image,
                folder=folder,
            )

            if i == 0:
                # print legend
                delta_title = ydelta_per_row if self.subtitle is None else (2 * ydelta_per_row)
                mat_fig.legend(lines, labels,
                    bbox_to_anchor=(0.0, title_y - delta_title),
                    loc='upper left',
                    ncol=legend_columns,
                    borderaxespad=0,
                    frameon=False
                )

            if self._create_subfigure_images:
                single_image = image_name.clone()
                single_image.add_key_value(place=self._dictonary_to_add_information, key="cumulativex", value=cumornot)
                single_image.add_key_value(place=self._dictonary_to_add_information, key="logy", value=logornot)

                self.xaxis.label.text = xaxis_base
                self.yaxis.label.text = yaxis_base

                single_figure = MatplotLibPlot2DGraph(
                    xaxis=self.xaxis,
                    yaxis=self.yaxis,
                    title=self.title,
                    subtitle=self.subtitle,
                )
                for p in plot_figure.plots():
                    single_figure.add_plot(p)

                single_figure.save_image(
                    image_name=single_image,
                    folder=folder,
                )


class MatplotLibPlot2DGraph(IPlot2DGraph):

    @property
    def title(self) -> "IText":
        return self._title

    @property
    def xaxis(self) -> "IAxis":
        return self._xaxis

    @property
    def yaxis(self) -> "IAxis":
        return self._yaxis

    @property
    def subtitle(self) -> Optional["IText"]:
        return self._subtitle

    @property
    def legend(self) -> "ILegend":
        return self._legend

    @property
    def grid(self) -> "IGrid":
        return self._grid

    def __init__(self, xaxis: IAxis, yaxis: IAxis, title: IText, subtitle: Optional[IText], use_provided_fig=None):
        self._title = title
        self._subtitle = subtitle
        self._xaxis = xaxis
        self._yaxis = yaxis
        self._legend = DefaultLegend(plot2dgraph=self)
        self._grid = DefaultGrid()
        self._plots = []
        self.use_provided_fig = use_provided_fig

    def add_plot(self, values: ISinglePlot):
        if self.contains_plot(values.label.text):
            raise ValueError(f"singleplot {values.label} is already present in the plot")
        self._plots.append(values)

    def get_plots(self, name: str) -> ISinglePlot:
        return list(filter(lambda p: p.label == name, self.plots()))[0]

    def contains_plot(self, name: str) -> bool:
        return len(list(filter(lambda p: p.label == name, self.plots()))) > 0

    def plots(self) -> Iterable[ISinglePlot]:
        return self._plots

    def plots_map(self) -> Iterable[Tuple[IAxis, ISinglePlot]]:
        return {p.label: p for p in self._plots}

    def save_image(self, image_name: KS001, folder: str = None, colon: str = ':', pipe: str = '|', underscore: str = '_', equal: str = '=') -> List[Tuple[str, KS001Str, DataTypeStr]]:
        image_filename_no_ext = image_name.dump_str(
            colon=colon,
            pipe=pipe,
            underscore=underscore,
            equal=equal
        )
        logging.info(f"saving image {image_filename_no_ext}")

        if self.use_provided_fig is not None:
            mat_ax = self.use_provided_fig
        else:
            mat_fig = plt.figure()
            mat_ax = mat_fig.add_subplot(1, 1, 1)

        if self.subtitle is not None:
            mat_title = f"{self.title.text}\n{self.subtitle.text}"
        else:
            mat_title = f"{self.title.text}"

        total_plots = len(self._plots)
        legend_columns = 3
        legend_rows = np.math.ceil(total_plots / legend_columns)
        ydelta_per_row = 0.05
        title_y = 1 + legend_rows * ydelta_per_row  # each row gives 0.05
        delta_title = ydelta_per_row if self.subtitle is None else (2 * ydelta_per_row)

        if self.legend.visible:
            mat_ax.set_title(mat_title, pad=0, loc="center", y=title_y)
        else:
            mat_ax.set_title(mat_title, pad=0, loc="center")

        mat_ax.set_xlabel(self._xaxis.label.text, fontdict={"size": self._xaxis.label.font_size})
        mat_ax.set_ylabel(self._yaxis.label.text, fontdict={"size": self._yaxis.label.font_size})

        mat_ax.xaxis.set_major_formatter(MatPlotCompliantFormatter(self.xaxis.formatter))
        mat_ax.yaxis.set_major_formatter(MatPlotCompliantFormatter(self.yaxis.formatter))

        extension = "eps"
        image_abspath = os.path.abspath(os.path.join(folder, image_filename_no_ext)) + f".{extension}"

        lines = []
        labels = []

        # we need to generate markers and differentiate marker position by a small delta (otherwise if 2 curves overlap
        # you don't see nor the curve nor the marker.
        # marker_number represents the number of marker that has a curve
        # marker_delta represents how much
        markers = itertools.cycle(('^', '+', 'x', 'd', '*'))
        marker_size = itertools.cycle((2, 2, 2, 2, 2))
        marker_number = 10

        plots = list(self.plots())

        for i, p in enumerate(plots):
            if len(p) != len(self._xaxis):
                raise ValueError(
                    f"xaxis is long {len(self._xaxis)} but the function {p.label} we want to draw is long {len(p)} points! There is something very wrong!")

            if self._xaxis.cumulative:
                actual_draw = np.cumsum(p)
            else:
                actual_draw = p

            marker_step = int(len(self.xaxis)/marker_number)
            if marker_step == 0:
                marker_step = 1

            if len(self.xaxis) >= len(plots):
                start_marker = i
            else:
                start_marker = 0

            line, = mat_ax.plot(
                list(self.xaxis.axis), list(actual_draw),
                label=p.label.text,
                linewidth=1,
                marker=next(markers),
                markevery=slice(start_marker, -1, marker_step),
                markersize=next(marker_size),
            )
            lines.append(line)
            labels.append(p.label.text)

            # if the curve has labels, we need to plot them
            if p.has_some_labels():
                for index, (x, (y, label)) in filter(lambda ax: ax[0] in range(start_marker, len(p), marker_step), enumerate(zip(self.xaxis.axis, p.values_and_labels()))):
                    mat_ax.annotate(
                        label,
                        xy=(x, y), xytext=(0, 10),
                        textcoords='offset points', ha='right', va='bottom',
                    )

        # x axis scale
        if self.xaxis.log10:
            mat_ax.set_xscale("log", basex=10)
        else:
            mat_ax.set_xscale("linear")

        # y axis scale
        if self.yaxis.log10:
            mat_ax.set_yscale("log", basey=10)
        else:
            mat_ax.set_yscale("linear")

        # grid
        if self.grid.visible:
            mat_ax.grid(True, axis='both')

        # legend
        if self.legend.visible:
            mat_ax.legend(lines, labels,
                          bbox_to_anchor=(0.0, title_y - delta_title),
                          loc='upper left',
                          ncol=legend_columns,
                          borderaxespad=0,
                          frameon=False
            )

        logging.info(f"creating image {image_abspath}")
        plt.savefig(image_abspath, bbox_inches='tight', format=extension)

        return [(image_abspath, image_filename_no_ext, extension)]
        #return labels, lines
