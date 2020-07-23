import operator as op
from itertools import cycle
from pathlib import Path
from typing import Mapping, Sequence

import attr
from bokeh.io.output import output_file
from bokeh.io.saving import save
from bokeh.models.sources import ColumnDataSource
from bokeh.plotting.figure import Figure, figure
from funcy import lmap

from .datastructures import LangDataPoint

COLORS = cycle(["cadetblue", "crimson", "peru", "olive"])
TOOLS = "pan,hover,wheel_zoom,box_zoom,save,reset,help"


@attr.s(auto_attribs=True, slots=True)
class Plotter(object):
    output_file: Path = attr.ib(converter=Path)
    title: str = attr.ib(default="Code Counts")

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

    def plot_counts(self, counts: Mapping[str, Sequence[LangDataPoint]]):
        output_file(
            str(self.output_file),
            title=self.title,
            root_dir=self.output_file.parent,
            mode="relative",
        )
        p = self.create_figure()
        for lang, lang_counts in counts.items():
            non_zero = [elem for elem in lang_counts if elem.code > 0]
            refs = lmap(op.attrgetter("commit.ref"), non_zero)
            subjects = lmap(op.attrgetter("commit.subject"), non_zero)
            dates = lmap(op.attrgetter("commit.dt"), non_zero)
            code = lmap(op.attrgetter("code"), non_zero)
            date_strs = [dt.strftime("%x") for dt in dates]
            count_strs = [f"{c:,}" for c in code]
            data = {
                "x": dates,
                "y": code,
                "date": date_strs,
                "count": count_strs,
                "ref": refs,
                "subject": subjects,
            }
            source = ColumnDataSource(data=data)
            self.plot_lang(p, lang, source)
        p.legend.location = "top_left"
        p.hover.tooltips = [
            ("Index", "$index"),
            ("Date", "@date"),
            ("LOC", "@count"),
            ("Message", "@subject"),
        ]
        save(p)
