import math
from datetime import datetime, timedelta, date, time
from functools import partial
from enum import Enum

from rich.text import Text
from textual import work
from textual.app import ComposeResult, RenderResult
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.geometry import Region
from textual.reactive import reactive
from textual.widgets import Button, Static
from textual.widget import Widget

from metaskingcli.api.log import (
    list_all,
)

DARK_BACKGROUND_FALLBACK = "grey27"
DARK_BACKGROUND_OPTIONS = [
    "rgb(0,45,112)",
    "rgb(22,90,90)",
    "rgb(0,97,60)",
    "rgb(72,72,0)",
    "rgb(97,19,0)",
    "rgb(56,0,112)",
]


DAY_SECONDS = 24 * 60 * 60
CALENDAR_HEIGHT = 96
FULL_HOUR_MARKERS = {
    int(i * CALENDAR_HEIGHT / 24): i for i in range(24)
}
# FULL_HOUR_MID_MARKERS = {
#     int(i * CALENDAR_HEIGHT / 24) + CALENDAR_HEIGHT / 24 / 2: i
#     for i in range(24)
# }


def _merge_ranges(
    ranges: list[tuple[float, float, str]],
) -> list[tuple[float, float, str]]:
    """Merge overlapping ranges."""

    if len(ranges) == 0:
        return []

    ranges = sorted(ranges, key=lambda r: r[0])

    i = 0
    merged_ranges = []
    while i < len(ranges):
        start, end, color = ranges[i]
        i += 1

        while i < len(ranges):
            next_start, next_end, next_color = ranges[i]
            if next_start <= end:
                end = max(end, next_end)
                if color != next_color:
                    color = DARK_BACKGROUND_FALLBACK
                ranges.pop(i)
            else:
                break

        merged_ranges.append((start, end, color))

    return merged_ranges


def _get_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


class WLCalCS(Enum):

    EMPTY = 0
    FULL = 1
    END_1 = 2
    END_2 = 3
    END_3 = 4
    END_4 = 5
    END_5 = 6
    END_6 = 7
    END_7 = 8
    START_1 = 9
    START_2 = 10
    START_3 = 11
    START_4 = 12
    START_5 = 13
    START_6 = 14
    START_7 = 15
    MIDDLE = 16  # (1/8 - 1/2) - (1/2 - 1/8)
    FUZZY = 17  # Multiple ranges

    def range_position(self) -> float:
        match self:
            case WLCalCS.EMPTY:
                return 0
            case WLCalCS.FULL:
                return 1
            case WLCalCS.END_1:
                return 1/8
            case WLCalCS.END_2:
                return 2/8
            case WLCalCS.END_3:
                return 3/8
            case WLCalCS.END_4:
                return 4/8
            case WLCalCS.END_5:
                return 5/8
            case WLCalCS.END_6:
                return 6/8
            case WLCalCS.END_7:
                return 7/8
            case WLCalCS.START_1:
                return 7/8
            case WLCalCS.START_2:
                return 6/8
            case WLCalCS.START_3:
                return 5/8
            case WLCalCS.START_4:
                return 4/8
            case WLCalCS.START_5:
                return 3/8
            case WLCalCS.START_6:
                return 2/8
            case WLCalCS.START_7:
                return 1/8
            case WLCalCS.MIDDLE:
                return 0.5
            case WLCalCS.FUZZY:
                return 0.5

    @staticmethod
    def from_ranges(
        ranges: list[tuple[float, float, str]],
    ) -> tuple["WLCalCS", str]:
        ranges = _merge_ranges(ranges)

        if len(ranges) == 0:
            return WLCalCS.EMPTY, DARK_BACKGROUND_FALLBACK

        if len(ranges) != 1:
            return WLCalCS.FUZZY, DARK_BACKGROUND_FALLBACK

        half_step = 1/16

        start, end, color = ranges[0]
        if start < half_step and end >= 1 - half_step:
            return WLCalCS.FULL, color

        if start < half_step:
            if end >= WLCalCS.END_7.range_position() - half_step:
                return WLCalCS.END_7, color
            if end >= WLCalCS.END_6.range_position() - half_step:
                return WLCalCS.END_6, color
            if end >= WLCalCS.END_5.range_position() - half_step:
                return WLCalCS.END_5, color
            if end >= WLCalCS.END_4.range_position() - half_step:
                return WLCalCS.END_4, color
            if end >= WLCalCS.END_3.range_position() - half_step:
                return WLCalCS.END_3, color
            if end >= WLCalCS.END_2.range_position() - half_step:
                return WLCalCS.END_2, color
            if end >= WLCalCS.END_1.range_position() - half_step:
                return WLCalCS.END_1, color
            return WLCalCS.EMPTY, color

        if end >= 1 - half_step:
            if start < WLCalCS.START_7.range_position() + half_step:
                return WLCalCS.START_7, color
            if start < WLCalCS.START_6.range_position() + half_step:
                return WLCalCS.START_6, color
            if start < WLCalCS.START_5.range_position() + half_step:
                return WLCalCS.START_5, color
            if start < WLCalCS.START_4.range_position() + half_step:
                return WLCalCS.START_4, color
            if start < WLCalCS.START_3.range_position() + half_step:
                return WLCalCS.START_3, color
            if start < WLCalCS.START_2.range_position() + half_step:
                return WLCalCS.START_2, color
            if start < WLCalCS.START_1.range_position() + half_step:
                return WLCalCS.START_1, color
            return WLCalCS.EMPTY, color

        if start >= half_step and \
                start < WLCalCS.START_4.range_position() + half_step and \
                end >= WLCalCS.END_4.range_position() - half_step and \
                end < 1 - half_step:
            return WLCalCS.MIDDLE, color

        return WLCalCS.FUZZY, color

    def as_text(self, color: str) -> Text:
        match self:
            case WLCalCS.EMPTY:
                return Text(" ", style=color, end="")
            case WLCalCS.FULL:
                return Text("█", style=color, end="")
            case WLCalCS.END_1:
                return Text("▔", style=color, end="")
            case WLCalCS.END_2:
                return Text("▂", style=color + " reverse", end="")
            case WLCalCS.END_3:
                return Text("▄", style=color + " reverse", end="")
            case WLCalCS.END_4:
                return Text("▀", style=color, end="")
            case WLCalCS.END_5:
                return Text("▅", style=color + " reverse", end="")
            case WLCalCS.END_6:
                return Text("▆", style=color + " reverse", end="")
            case WLCalCS.END_7:
                return Text("▇", style=color + " reverse", end="")
            case WLCalCS.START_1:
                return Text("▁", style=color, end="")
            case WLCalCS.START_2:
                return Text("▂", style=color, end="")
            case WLCalCS.START_3:
                return Text("▃", style=color, end="")
            case WLCalCS.START_4:
                return Text("▄", style=color, end="")
            case WLCalCS.START_5:
                return Text("▅", style=color, end="")
            case WLCalCS.START_6:
                return Text("▆", style=color, end="")
            case WLCalCS.START_7:
                return Text("▇", style=color, end="")
            case WLCalCS.MIDDLE:
                return Text("━", style=color, end="")
            case WLCalCS.FUZZY:
                return Text("░", style=color, end="")


class WorkLogCalendarDay(Widget):

    DEFAULT_CSS = """
    WorkLogCalendarDay {
        border: solid rgb(158,158,158);
        height: """ + str(CALENDAR_HEIGHT+2) + """;
        width: 1fr;
        color: rgb(178,178,178);
    }
    """

    logs_server: str
    day: reactive[date | None] = reactive(None)

    _ranges: list[tuple[float, float, str]] = []

    def __init__(
        self,
        server: str,
        day: date | None = None,
        **kwargs
    ) -> None:
        self.logs_server = server
        super().__init__(**kwargs)
        self.day = day

    def on_mount(self) -> None:
        self._refresh_data()

    def watch_day(self, new_value: date) -> None:
        self._ranges = []
        self.refresh(layout=True)
        self._refresh_data()

    def date_header(self) -> Text:
        width = self.size.width - 2
        width = max(width, 0)
        text = (" " * int(width / 2))
        if self.day is not None:
            text += self.day.strftime("%d")
        return Text(
            text,
            style="bold",
            end=""
        )

    def render(self) -> RenderResult:
        header = self.date_header()

        width = self.size.width
        height = CALENDAR_HEIGHT
        lines_ranges: list[list[tuple[float, float, str]]] = [
            []
            for _ in range(height)
        ]
        lines_texts: list[tuple[bool, str | None, str]] = [
            (False, None, "")
            for _ in range(height)
        ]

        for rstart, rend, name in self._ranges:
            color_index = hash(name) % len(DARK_BACKGROUND_OPTIONS)
            color = DARK_BACKGROUND_OPTIONS[color_index]

            rstart = min(max(rstart * height, 0), height)
            rend = min(max(rend * height, 0), height)

            istart = math.ceil(rstart)
            iend = int(rend)

            tstart = istart
            moved = False
            while tstart < height:
                _, text, _ = lines_texts[tstart]
                if text is None:
                    lines_texts[tstart] = (moved, name, color)
                    break
                tstart += 1
                moved = True

            mid_start: float | None = None
            mid_end: float | None = None
            if rstart % 1 != 0:
                mid_start = rstart % 1
            if rend % 1 != 0:
                mid_end = rend % 1

            if mid_start is not None and mid_end is not None and \
                    int(rstart) == int(rend):
                lines_ranges[int(rstart)].append((mid_start, mid_end, color))
                continue

            if mid_start is not None:
                lines_ranges[int(rstart)].append((mid_start, 1, color))

            if mid_end is not None:
                lines_ranges[int(rend)].append((0, mid_end, color))

            for i in range(istart, iend):
                lines_ranges[i].append((0, 1, color))

        output = Text()
        output.append(header)
        for i in range(height):
            output.append("\n")
            state, color = WLCalCS.from_ranges(lines_ranges[i])
            output.append(state.as_text(color))
            style = (
                "on " + color
                if state == WLCalCS.FULL else
                ""
            )
            was_moved, lname, lcolor = lines_texts[i]
            if lname is not None:
                space = "^" if was_moved else "="
                prefix_style = "on " + lcolor
                output.append(Text(
                    space,
                    style=prefix_style,
                    end="",
                ))
                rname = lname[:int(width-3)] + " "
                output.append(Text(
                    rname + " " * (int(width-2) - len(rname)),
                    style=style,
                    end="",
                ))
            else:
                output.append(Text(
                    (
                        "─" * int(width-1)
                        if i in FULL_HOUR_MARKERS else
                        " " * int(width-1)
                    ),
                    style=style,
                    end="",
                ))

        return output

    def refresh_data(self) -> None:
        self._ranges = []
        self.refresh(layout=True)
        self._refresh_data()

    @work(exclusive=True, group="calendar_refresh_data")
    async def _refresh_data(self) -> None:
        if self.day is None:
            return

        ranges = []

        since = datetime.combine(self.day, time.min)
        until = datetime.combine(self.day, time.max)

        async for log in list_all(
            self.logs_server,
            since=since,
            until=until,
            page_limit=20,
        ):
            for record in log['records']:
                start_time = datetime.fromisoformat(record['start'])
                end_time = (
                    datetime.fromisoformat(record['end'])
                    if record['end'] is not None
                    else datetime.now()
                )

                if start_time > until or end_time < since:
                    continue

                if start_time < since:
                    start_time = since
                if end_time > until:
                    end_time = until

                start = (start_time - since).total_seconds() / DAY_SECONDS
                end = (end_time - since).total_seconds() / DAY_SECONDS
                description = (
                    "" if log['description'] is None
                    else log['description']
                )
                range_name = f"{log['name']}: {description}"
                ranges.append((start, end, range_name))
            self._ranges = ranges.copy()
            self.call_after_refresh(partial(self.refresh, layout=True))

        self._ranges = ranges
        self.call_after_refresh(partial(self.refresh, layout=True))


class WorkLogCalendarHours(Widget):

    DEFAULT_CSS = """
    WorkLogCalendarHours {
        border: solid rgb(158,158,158);
        padding-left: 1;
        padding-right: 1;
        height: """ + str(CALENDAR_HEIGHT+2) + """;
        width: 6;
    }
    """

    def render(self) -> RenderResult:
        height = CALENDAR_HEIGHT

        lines = [
            Text(
                (
                    str(FULL_HOUR_MARKERS[i])
                    if i in FULL_HOUR_MARKERS
                    else ""
                ),
                style="bold",
                end="",
            )
            for i in range(height)
        ]

        output = Text("", end="")  # Header
        for line in lines:
            output.append("\n")
            output.append(line)

        return output


class WorkLogCalendar(ScrollableContainer):

    DEFAULT_CSS = """
    WorkLogCalendar .container-calendar-week {
        height: auto;
        width: 100%;
    }

    WorkLogCalendar .container-calendar-header {
        height: 3;
        width: 100%;
    }

    WorkLogCalendar .calendar-button-previous {
        dock: left;
    }

    WorkLogCalendar .calendar-button-next {
        dock: right;
    }

    WorkLogCalendar .calendar-date-heading {
        content-align: center middle;
        height: 3;
        width: 100%;
    }
    """

    logs_server: str
    week_start: reactive[date] = reactive(
        lambda: _get_week_start(date.today())
    )

    def __init__(
        self,
        server: str,
        **kwargs
    ) -> None:
        self.logs_server = server
        super().__init__(**kwargs)

    def on_mount(self) -> None:
        self.update_content()
        self.call_after_refresh(
            self.scroll_to_region,
            Region(
                0, CALENDAR_HEIGHT // 2,
                1, 1,
            ),
            center=True,
        )

    @property
    def week_end(self) -> date:
        return self.week_start + timedelta(days=7)

    def watch_week_start(self, old_value: date, new_value: date) -> None:
        if old_value == new_value:
            # This is called during initialization which is bad
            return

        self.update_content()

    def update_content(self) -> None:
        heading: Static = self.query_one(
            ".calendar-date-heading"
        )  # type: ignore
        heading.update(
            f"{self.week_start.strftime('%Y-%m-%d')} - " +
            f"{self.week_end.strftime('%Y-%m-%d')}"
        )

        for i in range(7):
            day: WorkLogCalendarDay = self.query_one(  # type: ignore
                f".container-calendar-day-{i}"
            )
            day.day = self.week_start + timedelta(days=i)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        button_name = event.button.name
        if button_name == "previous":
            self.week_start -= timedelta(days=7)
        elif button_name == "next":
            self.week_start += timedelta(days=7)

    def compose(self) -> ComposeResult:
        with Container(classes="container-calendar-header"):
            yield Button(
                "<",
                name="previous",
                classes="calendar-button-previous",
            )
            yield Static(
                classes="calendar-date-heading",
            )
            yield Button(
                ">",
                name="next",
                classes="calendar-button-next",
            )

        with Horizontal(classes="container-calendar-week"):
            yield WorkLogCalendarHours()
            for i in range(7):
                yield WorkLogCalendarDay(
                    self.logs_server,
                    classes=(
                        "container-calendar-day " +
                        "container-calendar-day-" + str(i)
                    ),
                )

    def refresh_data(self) -> None:
        for day_widget in self.query(WorkLogCalendarDay).results():
            day_widget.refresh_data()
