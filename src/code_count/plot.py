import operator as op
from itertools import cycle
from pathlib import Path
from typing import Mapping, Sequence

import attr
from bokeh.models import ColumnDataSource
from bokeh.palettes import Set2_8
from bokeh.plotting import Figure, figure, output_file, save, show
from funcy import lmap

from .datastructures import LangDataPoint

# COLORS = cycle(["cadetblue", "crimson", "peru", "olive"])
COLORS = cycle(Set2_8)
TOOLS = "pan,hover,wheel_zoom,box_zoom,save,reset,help"


@attr.s(auto_attribs=True, slots=True)
class Plotter(object):
    output_file: Path = attr.ib(converter=Path)
    title: str = attr.ib(default="Code Counts")
    fig: Figure = attr.ib(init=False)

    @classmethod
    def create(cls, output_file: Path) -> "Plotter":
        return cls(output_file)

    @fig.default
    def _make_fig(self):
        return self.create_figure()

    def create_figure(self) -> Figure:
        return figure(
            title=self.title,
            x_axis_label="Date",
            y_axis_label="Lines of Code",
            x_axis_type="datetime",
            plot_width=1400,
            plot_height=700,
            tools=TOOLS,
        )

    def plot_lang(self, fig: Figure, lang: str, source: ColumnDataSource):
        col = next(COLORS)
        common_kw = {
            "line_color": col,
            "source": source,
            "legend_label": f"{lang} Code Count",
        }
        fig.circle("x", "y", fill_color="white", size=8, **common_kw)
        fig.line("x", "y", line_width=2, **common_kw)

    def configure_fig(self):
        self.fig.title.text_font_size = "1.5rem"

        self.fig.axis.axis_label_text_font_size = "1rem"
        self.fig.axis.axis_label_text_font_style = "bold"

        x_ticker = self.fig.xaxis.ticker
        x_ticker.desired_num_ticks = 8
        x_ticker.num_minor_ticks = 5

        self.fig.sizing_mode = "stretch_both"
        self.fig.legend.location = "top_left"
        self.fig.hover.tooltips = [
            ("Index", "$index"),
            ("Date", "@date{%F}"),
            ("LOC", "@count{0,0}"),
            ("Message", "@subject"),
            ("Hash", "@ref"),
        ]
        self.fig.hover.formatters = {"@date": "datetime"}
        self.fig.toolbar.autohide = True

    def plot_counts(self, counts: Mapping[str, Sequence[LangDataPoint]]):
        output_file(
            str(self.output_file),
            title=self.title,
            root_dir=self.output_file.parent,
            mode="relative",
        )
        for lang, lang_counts in counts.items():
            non_zero = [elem for elem in lang_counts if elem.code > 0]
            subjects = lmap(op.attrgetter("commit.subject"), non_zero)
            dates = lmap(op.attrgetter("commit.dt"), non_zero)
            code = lmap(op.attrgetter("code"), non_zero)
            refs = lmap(
                op.itemgetter(slice(6)), map(op.attrgetter("commit.ref"), non_zero)
            )
            data = {
                "x": dates,
                "y": code,
                "date": dates,
                "count": code,
                "subject": subjects,
                "ref": refs,
            }
            source = ColumnDataSource(data=data)
            self.plot_lang(self.fig, lang, source)

        self.configure_fig()
        save(self.fig)

    def open_fig(self):
        show(self.fig)
