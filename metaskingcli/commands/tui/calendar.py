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

DAY_SECONDS = 24 * 60 * 60
CALENDAR_HEIGHT = 96
FULL_HOUR_MARKERS = {
    int(i * CALENDAR_HEIGHT / 24): i for i in range(24)
}


def _merge_ranges(
    ranges: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Merge overlapping ranges."""

    if len(ranges) == 0:
        return []

    ranges = sorted(ranges, key=lambda r: r[0])

    i = 0
    merged_ranges = []
    while i < len(ranges):
        start, end = ranges[i]
        i += 1

        while i < len(ranges):
            next_start, next_end = ranges[i]
            if next_start <= end:
                end = max(end, next_end)
                ranges.pop(i)
            else:
                break

        merged_ranges.append((start, end))

    return merged_ranges


def _get_week_start(date: date) -> date:
    return date - timedelta(days=date.weekday())


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
        ranges: list[tuple[float, float]],
    ) -> "WLCalCS":
        ranges = _merge_ranges(ranges)

        if len(ranges) == 0:
            return WLCalCS.EMPTY

        if len(ranges) != 1:
            return WLCalCS.FUZZY

        half_step = 1/16

        start, end = ranges[0]
        if start < half_step and end >= 1 - half_step:
            return WLCalCS.FULL

        if start < half_step:
            if end >= WLCalCS.END_7.range_position() - half_step:
                return WLCalCS.END_7
            if end >= WLCalCS.END_6.range_position() - half_step:
                return WLCalCS.END_6
            if end >= WLCalCS.END_5.range_position() - half_step:
                return WLCalCS.END_5
            if end >= WLCalCS.END_4.range_position() - half_step:
                return WLCalCS.END_4
            if end >= WLCalCS.END_3.range_position() - half_step:
                return WLCalCS.END_3
            if end >= WLCalCS.END_2.range_position() - half_step:
                return WLCalCS.END_2
            if end >= WLCalCS.END_1.range_position() - half_step:
                return WLCalCS.END_1
            return WLCalCS.EMPTY

        if end >= 1 - half_step:
            if start < WLCalCS.START_7.range_position() + half_step:
                return WLCalCS.START_7
            if start < WLCalCS.START_6.range_position() + half_step:
                return WLCalCS.START_6
            if start < WLCalCS.START_5.range_position() + half_step:
                return WLCalCS.START_5
            if start < WLCalCS.START_4.range_position() + half_step:
                return WLCalCS.START_4
            if start < WLCalCS.START_3.range_position() + half_step:
                return WLCalCS.START_3
            if start < WLCalCS.START_2.range_position() + half_step:
                return WLCalCS.START_2
            if start < WLCalCS.START_1.range_position() + half_step:
                return WLCalCS.START_1
            return WLCalCS.EMPTY

        if start >= half_step and \
                start < WLCalCS.START_4.range_position() + half_step and \
                end >= WLCalCS.END_4.range_position() - half_step and \
                end < 1 - half_step:
            return WLCalCS.MIDDLE

        return WLCalCS.FUZZY

    def as_text(self) -> Text:
        match self:
            case WLCalCS.EMPTY:
                return Text(" ", end="")
            case WLCalCS.FULL:
                return Text("█", end="")
            case WLCalCS.END_1:
                return Text("▔", end="")
            case WLCalCS.END_2:
                return Text("▂", style="reverse", end="")
            case WLCalCS.END_3:
                return Text("▄", style="reverse", end="")
            case WLCalCS.END_4:
                return Text("▀", end="")
            case WLCalCS.END_5:
                return Text("▅", style="reverse", end="")
            case WLCalCS.END_6:
                return Text("▆", style="reverse", end="")
            case WLCalCS.END_7:
                return Text("▇", style="reverse", end="")
            case WLCalCS.START_1:
                return Text("▁", end="")
            case WLCalCS.START_2:
                return Text("▂", end="")
            case WLCalCS.START_3:
                return Text("▃", end="")
            case WLCalCS.START_4:
                return Text("▄", end="")
            case WLCalCS.START_5:
                return Text("▅", end="")
            case WLCalCS.START_6:
                return Text("▆", end="")
            case WLCalCS.START_7:
                return Text("▇", end="")
            case WLCalCS.MIDDLE:
                return Text("━", end="")
            case WLCalCS.FUZZY:
                return Text("░", end="")


class WorkLogCalendarDay(Widget):

    DEFAULT_CSS = """
    WorkLogCalendarDay {
        border: solid cyan;
        height: """ + str(CALENDAR_HEIGHT+2) + """;
        width: 1fr;
        color: darkcyan;
    }
    """

    logs_server: str
    day: reactive[date] = reactive(date.today())

    _ranges: list[tuple[float, float, str]] = []

    def __init__(
        self,
        server: str,
        day: date,
        **kwargs
    ) -> None:
        self.logs_server = server
        super().__init__(**kwargs)
        self.day = day

    def on_mount(self) -> None:
        self.refresh_data()

    def watch_day(self, new_value: date) -> None:
        self._ranges = []
        self.refresh(layout=True)
        self.refresh_data()

    def date_header(self) -> Text:
        width = self.size.width - 2
        width = max(width, 0)
        return Text(
            self.day.strftime((" " * int(width / 2)) + "%d"),
            style="bold",
            end=""
        )

    def render(self) -> RenderResult:
        header = self.date_header()

        width = self.size.width
        height = CALENDAR_HEIGHT
        lines_ranges: list[list[tuple[float, float]]] = [
            []
            for _ in range(height)
        ]
        lines_texts: list[tuple[bool, str | None]] = [
            (False, None)
            for _ in range(height)
        ]

        for rstart, rend, name in self._ranges:
            rstart = min(max(rstart * height, 0), height)
            rend = min(max(rend * height, 0), height)

            istart = math.ceil(rstart)
            iend = int(rend)

            tstart = istart
            moved = False
            while tstart < height:
                _, text = lines_texts[tstart]
                if text is None:
                    lines_texts[tstart] = (moved, name)
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
                lines_ranges[int(rstart)].append((mid_start, mid_end))
                continue

            if mid_start is not None:
                lines_ranges[int(rstart)].append((mid_start, 1))

            if mid_end is not None:
                lines_ranges[int(rend)].append((0, mid_end))

            for i in range(istart, iend):
                lines_ranges[i].append((0, 1))

        output = header
        for i in range(height):
            output.append("\n")
            state = WLCalCS.from_ranges(lines_ranges[i])
            output.append(state.as_text())
            style = "reverse" if state == WLCalCS.FULL else ""
            was_moved, lname = lines_texts[i]
            if lname is not None:
                space = "^" if was_moved else " "
                rname = space + lname
                rname = rname[:int(width-2)] + " "
                output.append(Text(
                    rname + " " * (int(width-1) - len(rname)),
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

    @work(thread=True)
    def refresh_data(self) -> None:
        ranges = []

        since = datetime.combine(self.day, time.min)
        until = datetime.combine(self.day, time.max)

        offset = 0
        while True:
            logs = list_all(
                self.logs_server,
                since=since,
                until=until,
                offset=offset,
                limit=100,
            )

            if len(logs) == 0:
                break
            offset += len(logs)

            for log in logs:
                for record in log['records']:
                    start_time = datetime.fromisoformat(record['start'])
                    end_time = (
                        datetime.fromisoformat(record['end'])
                        if record['end'] is not None
                        else datetime.now()
                    )
                    start = (start_time - since).total_seconds() / DAY_SECONDS
                    end = (end_time - since).total_seconds() / DAY_SECONDS
                    description = (
                        "" if log['description'] is None
                        else log['description']
                    )
                    range_name = f"{log['name']}: {description}"
                    ranges.append((start, end, range_name))

        self._ranges = ranges
        self.call_after_refresh(partial(self.refresh, layout=True))


class WorkLogCalendarHours(Widget):

    DEFAULT_CSS = """
    WorkLogCalendarHours {
        border-top: solid cyan;
        border-bottom: solid cyan;
        height: """ + str(CALENDAR_HEIGHT+2) + """;
        width: 3;
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
                f"{self.week_start.strftime('%Y-%m-%d')} - " +
                f"{self.week_end.strftime('%Y-%m-%d')}",
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
                    self.week_start + timedelta(days=i),
                    classes=(
                        "container-calendar-day " +
                        "container-calendar-day-" + str(i)
                    ),
                )

    def refresh_data(self) -> None:
        for day_widget in self.query(WorkLogCalendarDay).results():
            day_widget.refresh_data()
