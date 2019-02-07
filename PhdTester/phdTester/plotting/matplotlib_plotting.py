import itertools
import logging
import os
from typing import Iterable, Tuple, Optional, Any, Union

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import Formatter

from phdTester import constants
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

    def save_image(self, image_filename_no_extension: Union[str, KS001], save_raw_data: bool, folder: str = None) -> Any:
        """

        :param image_filename_no_extension:
        :param folder:
        :param save_raw_data: True if you want to save the data of the subplots. To do something, you are required
        to save the subplots as well!
        :return:
        """

        if isinstance(image_filename_no_extension, str):
            multi_image = "{filename}{pipe}mode{equal}multi".format(
                    filename=image_filename_no_extension,
                    colon=constants.SEP_COLON,
                    pipe=constants.SEP_PIPE,
                    equal=constants.SEP_KEYVALUE,
                    underscore=constants.SEP_PAIRS,
                )
        elif isinstance(image_filename_no_extension, KS001):
            multi_image = image_filename_no_extension.clone()
            multi_image.add_key_value(place=self._dictonary_to_add_information, key="mode", value="multi")
        else:
            TypeError(f"invalid type {type(image_filename_no_extension)}! Only str or KS001 as accepted!")

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
            imagex = ""
            imagey = ""

            if cumornot:
                xperks.append('cumulative')
                imagex = 'cumulative'
            else:
                xperks.append('linear')
                imagex = 'linear'

            if logornot:
                yperks.append('log10')
                imagey = 'log'
            else:
                yperks.append('identity')
                imagey = 'linear'

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
                image_filename_no_extension=multi_image,
                folder=folder,
                save_raw_data=False,
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

                if isinstance(image_filename_no_extension, str):
                    single_image = "{filename}{pipe}mode{equal}single{underscore}x{equal}{imagex}{underscore}y{equal}{imagey}".format(
                        filename=image_filename_no_extension,
                        colon=constants.SEP_COLON,
                        pipe=constants.SEP_PIPE,
                        equal=constants.SEP_KEYVALUE,
                        underscore=constants.SEP_PAIRS,
                        imagex=imagex,
                        imagey=imagey
                    )
                elif isinstance(image_filename_no_extension, KS001):
                    single_image = image_filename_no_extension.clone()
                    single_image.add_key_value(place=self._dictonary_to_add_information, key="mode", value="single")
                    single_image.add_key_value(place=self._dictonary_to_add_information, key="x", value=imagex)
                    single_image.add_key_value(place=self._dictonary_to_add_information, key="y", value=imagey)
                else:
                    TypeError(f"invalid type {type(image_filename_no_extension)}! Only str or KS001 as accepted!")

                single_figure.save_image(
                    image_filename_no_extension=single_image,
                    folder=folder,
                    save_raw_data=save_raw_data,
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

    def __init__(self, xaxis: IAxis, yaxis: IAxis, title:IText, subtitle: Optional[IText], use_provided_fig=None):
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

    def save_image(self, image_filename_no_extension: Union[str, KS001], save_raw_data: bool, folder: str = None) -> Any:
        if isinstance(image_filename_no_extension, str):
            if not os.path.isabs(image_filename_no_extension):
                image_filename_no_extension = os.path.abspath(os.path.join(folder, image_filename_no_extension))
        elif isinstance(image_filename_no_extension, KS001):
            image_filename_no_extension = image_filename_no_extension.dump_str(
                colon=constants.SEP_COLON,
                pipe=constants.SEP_PIPE,
                underscore=constants.SEP_PAIRS,
                equal=constants.SEP_KEYVALUE
            )
            image_filename_no_extension = os.path.abspath(os.path.join(folder, image_filename_no_extension))
        else:
            raise TypeError(f"invalid type {type(image_filename_no_extension)}! Only str or KS001 are accepted!")

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
        final_image = f"{os.path.abspath(image_filename_no_extension)}.{extension}"

        lines = []
        labels = []

        # we need to generate markers and differentiate marker position by a small delta (otherwise if 2 curves overlap
        # you don't see nor the curve nor the marker.
        # marker_number represents the number of marker that has a curve
        # marker_delta represents how much
        markers = itertools.cycle(('^', '+', 'x', 'd', '*'))
        marker_size = itertools.cycle((2, 2, 2, 2, 2))
        marker_number = 10
        for i, p in enumerate(self.plots()):
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

            if len(self.xaxis) >= len(self.plots()):
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

        # we need to save the actual data we're printing?
        if save_raw_data:
            self._save_raw_data(image_filename_no_extension)

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
            # ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.01), borderaxespad=0, frameon=False)
            # ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05),
            #          ncol=1, fancybox=True, shadow=True)

        logging.info(f"creating image {final_image}")
        plt.savefig(final_image, bbox_inches='tight', format=extension)

        return labels, lines
