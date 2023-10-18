from typing import Any, Callable, Mapping, Iterable
import math
from datetime import datetime, timedelta, date, time
from functools import partial
from enum import Enum

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult, RenderResult as TextualRenderResult
from textual._system_commands import SystemCommands
from textual.command import Hit, Hits, Provider
from textual.binding import Binding
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.events import Key
from textual.geometry import Region
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Static, Tabs, Tab
from textual.widget import Widget

from metaskingcli.api.log import (
    get_active,
    list_all,
    stop_all,
    stop_active,
    stop,
    start,
    next,
    pause_active,
    pause,
    resume,
    delete,
    update
)


class BarCS(Enum):
    EMPTY = 0
    FULL = 1
    LEFT = 2
    RIGHT = 3

    def merge(self, other: "BarCS") -> "BarCS":
        if self == BarCS.EMPTY:
            return other
        elif self == BarCS.FULL:
            return self
        elif self == BarCS.LEFT:
            if other == BarCS.RIGHT:
                return BarCS.FULL
            elif other == BarCS.FULL:
                return other
            else:
                return self
        elif self == BarCS.RIGHT:
            if other == BarCS.LEFT:
                return BarCS.FULL
            elif other == BarCS.FULL:
                return other
            else:
                return self
        else:
            raise Exception("Unknown state")


class Bar:
    def __init__(
        self,
        highlighted_ranges: list[tuple[float, float]] = [],
    ) -> None:
        self.highlighted_ranges = highlighted_ranges

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        highlight_style = console.get_style("dark_cyan")
        background_style = console.get_style("grey37")

        width = options.max_width
        content: list[BarCS] = list(
            BarCS.EMPTY for _ in range(width)
        )

        for highlight_range in self.highlighted_ranges:
            start, end = highlight_range

            start *= width
            end *= width

            start = max(start, 0)
            end = min(end, width)

            underflow = start % 1
            overflow = end % 1

            start = int(start)
            if underflow >= 0.5:
                content[start] = content[start]\
                    .merge(BarCS.LEFT)
                start += 1

            end = int(end)
            if overflow >= 0.5:
                content[end + 1] = content[end + 1]\
                    .merge(BarCS.RIGHT)

            for i in range(start, end):
                content[i] = content[i].merge(BarCS.FULL)

        for i in range(len(content)):
            c_prev = content[i - 1] if i > 0 else None
            c_curr = content[i]
            c_next = content[i + 1] if i < len(content) - 1 else None

            # E -> E '━━'
            # E -> L '━╺'
            # E -> R '╸╸'
            # E -> F '╸━'
            # L -> E '╺╺'
            # L -> L '╺╺'
            # L -> R '╺╸'
            # L -> F '╺━'
            # R -> E '╸━'
            # R -> L '╸╺'
            # R -> R '╸╸'
            # R -> F '╸━'
            # F -> E '━╺'
            # F -> L '━╺'
            # F -> R '━╸'
            # F -> F '━━'

            match (c_prev, c_curr, c_next):
                case (BarCS.EMPTY, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.EMPTY, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.EMPTY, BarCS.EMPTY, None) | \
                        (BarCS.RIGHT, BarCS.EMPTY, None) | \
                        (None, BarCS.EMPTY, BarCS.EMPTY) | \
                        (None, BarCS.EMPTY, BarCS.LEFT):
                    yield Text("━", style=background_style, end="")
                case (BarCS.LEFT, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.LEFT, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.LEFT, BarCS.EMPTY, None) | \
                        (BarCS.FULL, BarCS.EMPTY, None):
                    yield Text("╺", style=background_style, end="")
                case (BarCS.EMPTY, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.EMPTY, BarCS.EMPTY, BarCS.FULL) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.FULL) | \
                        (None, BarCS.EMPTY, BarCS.RIGHT) | \
                        (None, BarCS.EMPTY, BarCS.FULL):
                    yield Text("╸", style=background_style, end="")
                case (BarCS.LEFT, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.LEFT, BarCS.EMPTY, BarCS.FULL) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.FULL):
                    # This is conflict between two conversions
                    # Let's just add space - there will be more blank space
                    yield Text(" ", style=background_style, end="")
                case (_, BarCS.LEFT, _):
                    yield Text("╺", style=highlight_style, end="")
                case (_, BarCS.RIGHT, _):
                    yield Text("╸", style=highlight_style, end="")
                case (_, BarCS.FULL, _):
                    yield Text("━", style=highlight_style, end="")
                case _:
                    raise Exception("Unhandled bar state")

        # Fire actions when certain ranges are clicked (e.g. for tabs)
        # for range_name, (start, end) in self.clickable_ranges.items():
        #     output_bar.apply_meta(
        #         {"@click": f"range_clicked('{range_name}')"}, start, end
        #     )

        pass


class EditableStatic(Static, can_focus=True):
    """A widget that displays a static text and allows to edit it."""

    # Without min-width and min-height the user can't click on the widget
    DEFAULT_CSS = """
    EditableStatic {
        min-width: 2;
        min-height: 1;
    }
    """

    text: reactive[str | None] = reactive(None)
    cursor:  reactive[int] = reactive(0)
    fallback_text: str
    save_callback: Callable[[str | None], Any] | None = None

    def __init__(
        self,
        text: str | None = None,
        fallback_text: str = "",
        save_callback: Callable[[str | None], Any] | None = None,
        **kwargs
    ) -> None:
        self.fallback_text = fallback_text
        self.save_callback = save_callback
        super().__init__(self.resolve_text(text), **kwargs)
        self.text = text
        self.cursor = len(self.text or "")

    def resolve_text(self, text: str | None) -> str:
        if text is None:
            if self.has_focus:
                return ""
            else:
                return self.fallback_text
        return text

    def add_cursor(self, text: str) -> str:
        if self.has_focus:
            return text[:self.cursor] + "|" + text[self.cursor:]
        return text

    def update_text(self) -> None:
        self.update(self.add_cursor(self.resolve_text(self.text)))

    def watch_text(self, new_value: str | None) -> None:
        self.call_after_refresh(self.update_text)

    def watch_cursor(self, new_value: int) -> None:
        self.call_after_refresh(self.update_text)

    def on_focus(self, event) -> None:
        self.call_after_refresh(self.update_text)

    def on_blur(self, event) -> None:
        self.call_after_refresh(self.update_text)

    def key_enter(self) -> None:
        if self.save_callback is not None:
            self.save_callback(self.text)
        self.blur()

    def key_escape(self) -> None:
        self.blur()

    def key_home(self) -> None:
        self.cursor = 0

    def key_end(self) -> None:
        if self.text is None:
            return
        self.cursor = len(self.text)

    def key_backspace(self) -> None:
        if self.text is None:
            return

        if self.cursor == 0:
            return

        text = self.text[:self.cursor - 1] + self.text[self.cursor:]
        self.cursor -= 1
        self.text = text

    def key_delete(self) -> None:
        if self.text is None:
            return

        if self.cursor >= len(self.text):
            return

        text = self.text[:self.cursor] + self.text[self.cursor + 1:]
        self.text = text

    def key_left(self) -> None:
        if self.cursor == 0:
            return

        self.cursor -= 1

    def key_right(self) -> None:
        if self.text is None:
            return

        if self.cursor >= len(self.text):
            return

        self.cursor += 1

    def on_key(self, event: Key) -> None:
        if event.character is None or not event.is_printable:
            return

        text = self.text
        if text is None:
            text = ""

        text = text[:self.cursor] + event.character + text[self.cursor:]
        self.cursor += 1
        self.text = text


class WorkLog(Static):
    """A widget that displays a work log."""

    DEFAULT_CSS = """
    WorkLog {
        layout: horizontal;
        background: $boost;
        height: 7;
        margin: 1;
        min-width: 50;
        padding: 1;
    }

    WorkLog .log-category {
        min-height: 1;
        width: auto;
        color: cyan;
    }

    WorkLog .log-task {
        min-height: 1;
        width: auto;
        color: yellow;
    }

    WorkLog .log-id {
        min-height: 1;
        width: auto;
        color: red;
    }

    WorkLog .log-name {
        min-height: 1;
        width: auto;
        color: green;
    }

    WorkLog .log-flags {
        min-height: 1;
        width: auto;
        color: magenta;
    }

    WorkLog .log-identifiers {
        height: 5;
        width: auto;
        dock: left;
    }

    WorkLog .log-visualization {
        width: 100%;
        height: 1;
    }

    WorkLog .log-date {
        text-opacity: 80%;
        width: 100%;
        height: 1;
    }

    WorkLog .log-time {
        text-opacity: 80%;
        width: 100%;
        height: 1;
    }

    WorkLog .log-description {
        content-align: center middle;
        text-opacity: 80%;
        width: 100%;
        height: 2;
    }

    WorkLog .log-description :focus {
        text-opacity: 100%;
    }

    WorkLog .log-middle {
        width: 100%;
        height: 5;
        border-left: solid darkgray;
        border-right: solid darkgray;
        margin-left: 1;
        margin-right: 1;
        padding-left: 1;
        padding-right: 1;
    }

    WorkLog .log-buttons {
        dock: right;
        height: 5;
        width: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    WorkLog .log-button {
    }

    WorkLog .log-resume {
        background: $success;
    }

    WorkLog .log-pause {
        background: $warning;
    }

    WorkLog .log-stop {
        background: darkorange;
    }

    WorkLog .log-edit {
        background: darkcyan;
    }

    WorkLog .log-delete {
        background: $error;
    }
    """

    _refresh_app: Callable[[], None]
    _logs_server: str
    _read_only_mode: bool
    _log: dict[str, Any]

    start_date: str
    end_date: str
    start_time: str
    end_time: str
    activity_ranges: list[tuple[float, float]]
    active: bool

    def __init__(
        self,
        refresh_app: Callable[[], None],
        logs_server: str,
        log: dict[str, Any],
        read_only_mode: bool = False,
        **kwargs
    ) -> None:
        self._refresh_app = refresh_app
        self._logs_server = logs_server
        self._read_only_mode = read_only_mode
        self._log = log

        self.start_date = "No records"
        self.end_date = "No records"
        self.start_time = "--:--:--"
        self.end_time = "--:--:--"
        self.activity_ranges = []
        self.active = False

        if len(self._log['records']) > 0:
            log_start = datetime.fromisoformat(
                self._log['records'][0]['start']
            )

            self.start_date = log_start.strftime("%Y-%m-%d")
            self.start_time = log_start.strftime("%H:%M:%S")

            log_end_str = self._log['records'][-1]['end']
            log_end = datetime.now()

            if log_end_str is not None:
                log_end = datetime.fromisoformat(log_end_str)
                self.end_date = log_end.strftime("%Y-%m-%d")
                self.end_time = log_end.strftime("%H:%M:%S")
            else:
                self.end_date = self.start_date
                self.active = True

            duration = (log_end - log_start).total_seconds()

            def get_activity_range(
                record: dict[str, Any]
            ) -> tuple[float, float]:
                start_time = datetime.fromisoformat(record['start'])
                start = (start_time - log_start).total_seconds() / duration
                if record['end'] is None:
                    return (start, duration)

                end_time = datetime.fromisoformat(record['end'])
                end = (end_time - log_start).total_seconds() / duration
                return (start, end)

            self.activity_ranges = list(map(
                get_activity_range,
                self._log['records'],
            ))

        super().__init__(**kwargs)

    @work(thread=True)
    def save_category(self, category: str | None) -> None:
        update(
            self._logs_server,
            self._log['id'],
            create_category=True,
            category=category,
        )

    @work(thread=True)
    def save_task(self, task: str | None) -> None:
        update(
            self._logs_server,
            self._log['id'],
            create_task=True,
            task=task,
        )

    @work(thread=True)
    def save_name(self, name: str | None) -> None:
        update(
            self._logs_server,
            self._log['id'],
            name=name,
        )

    @work(thread=True)
    def save_description(self, description: str | None) -> None:
        update(
            self._logs_server,
            self._log['id'],
            description=description,
        )

    def compose(self) -> ComposeResult:
        with Container(classes="log-identifiers"):
            yield EditableStatic(
                (
                    self._log['category']['name']
                    if self._log['category'] else None
                ),
                fallback_text="Default",
                save_callback=self.save_category,
                classes="log-category"
            )
            yield EditableStatic(
                (
                    self._log['task']['name']
                    if self._log['task'] else None
                ),
                fallback_text="Default",
                save_callback=self.save_task,
                classes="log-task"
            )

            yield Static(str(self._log['id']), classes="log-id")
            yield EditableStatic(
                self._log['name'],
                fallback_text="---",
                save_callback=self.save_name,
                classes="log-name"
            )
            yield Static(
                '[' + (','.join(self._log['flags'])) + ']',
                classes="log-flags"
            )

        with Container(classes="log-middle"):
            yield Static(
                Bar(self.activity_ranges),
                classes="log-visualization"
            )

            date_str = self.start_date
            if self.start_date != self.end_date:
                date_str += " - " + self.end_date
            yield Static(date_str, classes="log-date")

            time_str = self.start_time + " - " + self.end_time
            yield Static(time_str, classes="log-time")

            yield EditableStatic(
                self._log['description'],
                fallback_text="No description",
                save_callback=self.save_description,
                classes="log-description"
            )

        with Horizontal(classes="log-buttons"):
            if self._read_only_mode:
                return

            if not self._log['stopped']:
                yield Button(
                    "Stop",
                    name="stop",
                    classes="log-button log-stop"
                )

            if self.active:
                yield Button(
                    "Pause",
                    name="pause",
                    classes="log-button log-pause"
                )
            else:
                yield Button(
                    "Resume",
                    name="resume",
                    classes="log-button log-resume"
                )

            # yield Button(
            #     "Edit",
            #     name="edit",
            #     classes="log-button log-edit"
            # )
            yield Button(
                "Delete",
                name="delete",
                classes="log-button log-delete"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        button_name = event.button.name
        if button_name == "stop":
            stop(self._logs_server, self._log['id'])
        elif button_name == "pause":
            pause(self._logs_server, self._log['id'])
        elif button_name == "resume":
            resume(self._logs_server, self._log['id'])
        elif button_name == "edit":
            # TODO: Implement edit
            pass
        elif button_name == "delete":
            delete(self._logs_server, self._log['id'])

        self._refresh_app()


class AutoLoadScrollableContainer(ScrollableContainer):

    scroll_end_callback: Callable[[], None] | None = None

    def __init__(
        self,
        *containers: Container,
        scroll_end_callback: Callable[[], None] | None = None,
        **kwargs
    ) -> None:
        self.scroll_end_callback = scroll_end_callback
        super().__init__(*containers, **kwargs)

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        edge = self.max_scroll_y - 5
        if old_value <= edge and new_value > edge:
            if self.scroll_end_callback is not None:
                self.call_after_refresh(self.scroll_end_callback)

        return super().watch_scroll_y(old_value, new_value)


class LogList(ScrollableContainer):

    reload_all_logs: Callable[[], None]
    read_only_mode: bool
    logs_server: str
    logs_only_active: bool | None = None
    logs_filters: Mapping[str, Any] = {}
    logs_reached_end: bool = False
    logs_offset: int = 0

    def __init__(
        self,
        server: str,
        only_active: bool | None = None,
        filters: Mapping[str, Any] | None = None,
        reload_all_logs: Callable[[], None] | None = None,
        read_only_mode: bool = False,
        **kwargs
    ) -> None:
        self.logs_server = server
        self.logs_only_active = only_active
        self.logs_filters = filters or {}
        self.reload_all_logs = reload_all_logs or self.reload_logs
        self.read_only_mode = read_only_mode
        super().__init__(classes="container-logs-wrapper", **kwargs)
        self.add_class("container-logs-wrapper-empty")

    def reload_logs(self) -> None:
        self.logs_reached_end = False
        self.logs_offset = 0
        self.query_one(".container-logs").remove_children()
        self.add_class("container-logs-wrapper-empty")
        self.load_more_logs()

    def _add_logs(
        self,
        offset: int,
        reached_end: bool,
        logs: list[dict[str, Any]]
    ) -> None:
        if offset != self.logs_offset:
            # Race condition - ignore
            return

        self.logs_offset += len(logs)
        self.logs_reached_end = reached_end

        widgets: Iterable[WorkLog] = map(
            lambda log: WorkLog(
                self.reload_all_logs,
                self.logs_server,
                log,
                read_only_mode=self.read_only_mode
            ),
            logs,
        )

        if self.logs_only_active is False:
            widgets = filter(
                lambda log: not log.active,
                widgets
            )

        widgets_list = list(widgets)

        self.query_one(".container-logs").mount_all(widgets_list)

        if len(widgets_list) != 0:
            self.remove_class("container-logs-wrapper-empty")

    @work(exclusive=True, thread=True)
    def load_more_logs(self) -> None:
        reached_end = self.logs_reached_end
        offset = self.logs_offset

        if reached_end:
            return

        if self.logs_only_active:
            logs = []
            active_log = get_active(self.logs_server)
            if active_log is not None:
                logs.append(active_log)
            reached_end = True
        else:
            logs = list_all(
                self.logs_server,
                offset=self.logs_offset,
                limit=20,
                **self.logs_filters
            )
            if len(logs) < 20:
                reached_end = True

        self.call_after_refresh(self._add_logs, offset, reached_end, logs)

    def compose(self) -> ComposeResult:
        yield Static("No logs", classes="no-logs")
        yield Container(classes="container-logs")

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        edge = self.max_scroll_y - 5
        if old_value <= edge and new_value > edge:
            self.call_after_refresh(self.load_more_logs)

        return super().watch_scroll_y(old_value, new_value)


DAY_SECONDS = 24 * 60 * 60
CALENDAR_HEIGHT = 96
FULL_HOUR_MARKERS = {
    int(i * CALENDAR_HEIGHT / 24): i for i in range(24)
}


def _get_week_start(date: date) -> date:
    return date - timedelta(days=date.weekday())


class WorkLogCalendarHours(Widget):

    DEFAULT_CSS = """
    WorkLogCalendarHours {
        border-top: solid cyan;
        border-bottom: solid cyan;
        height: """ + str(CALENDAR_HEIGHT+2) + """;
        width: 3;
    }
    """

    def render(self) -> TextualRenderResult:
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


def merge_ranges(
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


class WLCalCS(Enum):

    EMPTY = 0
    FULL = 1
    END_1 = 2  # 1/8
    END_2 = 3  # 1/4
    END_3 = 4  # 3/8
    END_4 = 5  # 1/2
    END_5 = 6  # 5/8
    END_6 = 7  # 3/4
    END_7 = 8  # 7/8
    START_1 = 9  # 1/8
    START_2 = 10  # 1/4
    START_3 = 11  # 3/8
    START_4 = 12  # 1/2
    START_5 = 13  # 5/8
    START_6 = 14  # 3/4
    START_7 = 15  # 7/8
    MIDDLE = 16  # (start 1/8 - 1/2) - (end 1/2 - 1/8)
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
        ranges = merge_ranges(ranges)

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

    # def merge(self, other: "WLCalCS") -> "WLCalCS":
    #     match (self, other):
    #         # At least one full
    #         case (WLCalCS.FULL, _) | \
    #                 (_, WLCalCS.FULL):
    #             return WLCalCS.FULL
    #         # Both empty
    #         case (WLCalCS.EMPTY, WLCalCS.EMPTY):
    #             return WLCalCS.EMPTY
    #         # Both same
    #         case (WLCalCS.END_1, WLCalCS.END_1) | \
    #                 (WLCalCS.END_2, WLCalCS.END_2) | \
    #                 (WLCalCS.END_3, WLCalCS.END_3) | \
    #                 (WLCalCS.END_4, WLCalCS.END_4) | \
    #                 (WLCalCS.END_5, WLCalCS.END_5) | \
    #                 (WLCalCS.END_6, WLCalCS.END_6) | \
    #                 (WLCalCS.END_7, WLCalCS.END_7) | \
    #                 (WLCalCS.START_1, WLCalCS.START_1) | \
    #                 (WLCalCS.START_2, WLCalCS.START_2) | \
    #                 (WLCalCS.START_3, WLCalCS.START_3) | \
    #                 (WLCalCS.START_4, WLCalCS.START_4) | \
    #                 (WLCalCS.START_5, WLCalCS.START_5) | \
    #                 (WLCalCS.START_6, WLCalCS.START_6) | \
    #                 (WLCalCS.START_7, WLCalCS.START_7) | \
    #                 (WLCalCS.MIDDLE, WLCalCS.MIDDLE):
    #             return self
    #         # Both add up to exactly full
    #         case (WLCalCS.END_1, WLCalCS.START_7) | \
    #                 (WLCalCS.END_2, WLCalCS.START_6) | \
    #                 (WLCalCS.END_3, WLCalCS.START_5) | \
    #                 (WLCalCS.END_4, WLCalCS.START_4) | \
    #                 (WLCalCS.END_5, WLCalCS.START_3) | \
    #                 (WLCalCS.END_6, WLCalCS.START_2) | \
    #                 (WLCalCS.END_7, WLCalCS.START_1) | \
    #                 (WLCalCS.START_1, WLCalCS.END_7) | \
    #                 (WLCalCS.START_2, WLCalCS.END_6) | \
    #                 (WLCalCS.START_3, WLCalCS.END_5) | \
    #                 (WLCalCS.START_4, WLCalCS.END_4) | \
    #                 (WLCalCS.START_5, WLCalCS.END_3) | \
    #                 (WLCalCS.START_6, WLCalCS.END_2) | \
    #                 (WLCalCS.START_7, WLCalCS.END_1):
    #             return WLCalCS.FULL
    #         # Both start, but first starts earlier
    #         case (WLCalCS.START_7, WLCalCS.START_1) | \
    #                 (WLCalCS.START_7, WLCalCS.START_2) | \
    #                 (WLCalCS.START_7, WLCalCS.START_3) | \
    #                 (WLCalCS.START_7, WLCalCS.START_4) | \
    #                 (WLCalCS.START_7, WLCalCS.START_5) | \
    #                 (WLCalCS.START_7, WLCalCS.START_6) | \
    #                 (WLCalCS.START_6, WLCalCS.START_1) | \
    #                 (WLCalCS.START_6, WLCalCS.START_2) | \
    #                 (WLCalCS.START_6, WLCalCS.START_3) | \
    #                 (WLCalCS.START_6, WLCalCS.START_4) | \
    #                 (WLCalCS.START_6, WLCalCS.START_5) | \
    #                 (WLCalCS.START_5, WLCalCS.START_1) | \
    #                 (WLCalCS.START_5, WLCalCS.START_2) | \
    #                 (WLCalCS.START_5, WLCalCS.START_3) | \
    #                 (WLCalCS.START_5, WLCalCS.START_4) | \
    #                 (WLCalCS.START_4, WLCalCS.START_1) | \
    #                 (WLCalCS.START_4, WLCalCS.START_2) | \
    #                 (WLCalCS.START_4, WLCalCS.START_3) | \
    #                 (WLCalCS.START_3, WLCalCS.START_1) | \
    #                 (WLCalCS.START_3, WLCalCS.START_2) | \
    #                 (WLCalCS.START_2, WLCalCS.START_1):
    #             return self
    #         # Both start, but second starts earlier
    #         case (WLCalCS.START_1, WLCalCS.START_7) | \
    #                 (WLCalCS.START_2, WLCalCS.START_7) | \
    #                 (WLCalCS.START_3, WLCalCS.START_7) | \
    #                 (WLCalCS.START_4, WLCalCS.START_7) | \
    #                 (WLCalCS.START_5, WLCalCS.START_7) | \
    #                 (WLCalCS.START_6, WLCalCS.START_7) | \
    #                 (WLCalCS.START_1, WLCalCS.START_6) | \
    #                 (WLCalCS.START_2, WLCalCS.START_6) | \
    #                 (WLCalCS.START_3, WLCalCS.START_6) | \
    #                 (WLCalCS.START_4, WLCalCS.START_6) | \
    #                 (WLCalCS.START_5, WLCalCS.START_6) | \
    #                 (WLCalCS.START_1, WLCalCS.START_5) | \
    #                 (WLCalCS.START_2, WLCalCS.START_5) | \
    #                 (WLCalCS.START_3, WLCalCS.START_5) | \
    #                 (WLCalCS.START_4, WLCalCS.START_5) | \
    #                 (WLCalCS.START_1, WLCalCS.START_4) | \
    #                 (WLCalCS.START_2, WLCalCS.START_4) | \
    #                 (WLCalCS.START_3, WLCalCS.START_4) | \
    #                 (WLCalCS.START_1, WLCalCS.START_3) | \
    #                 (WLCalCS.START_2, WLCalCS.START_3) | \
    #                 (WLCalCS.START_1, WLCalCS.START_2):
    #             return other
    #         # Both end, but first ends later
    #         case (WLCalCS.END_7, WLCalCS.END_1) | \
    #                 (WLCalCS.END_7, WLCalCS.END_2) | \
    #                 (WLCalCS.END_7, WLCalCS.END_3) | \
    #                 (WLCalCS.END_7, WLCalCS.END_4) | \
    #                 (WLCalCS.END_7, WLCalCS.END_5) | \
    #                 (WLCalCS.END_7, WLCalCS.END_6) | \
    #                 (WLCalCS.END_6, WLCalCS.END_1) | \
    #                 (WLCalCS.END_6, WLCalCS.END_2) | \
    #                 (WLCalCS.END_6, WLCalCS.END_3) | \
    #                 (WLCalCS.END_6, WLCalCS.END_4) | \
    #                 (WLCalCS.END_6, WLCalCS.END_5) | \
    #                 (WLCalCS.END_5, WLCalCS.END_1) | \
    #                 (WLCalCS.END_5, WLCalCS.END_2) | \
    #                 (WLCalCS.END_5, WLCalCS.END_3) | \
    #                 (WLCalCS.END_5, WLCalCS.END_4) | \
    #                 (WLCalCS.END_4, WLCalCS.END_1) | \
    #                 (WLCalCS.END_4, WLCalCS.END_2) | \
    #                 (WLCalCS.END_4, WLCalCS.END_3) | \
    #                 (WLCalCS.END_3, WLCalCS.END_1) | \
    #                 (WLCalCS.END_3, WLCalCS.END_2) | \
    #                 (WLCalCS.END_2, WLCalCS.END_1):
    #             return self
    #         # Both end, but second ends later
    #         case (WLCalCS.END_1, WLCalCS.END_7) | \
    #                 (WLCalCS.END_2, WLCalCS.END_7) | \
    #                 (WLCalCS.END_3, WLCalCS.END_7) | \
    #                 (WLCalCS.END_4, WLCalCS.END_7) | \
    #                 (WLCalCS.END_5, WLCalCS.END_7) | \
    #                 (WLCalCS.END_6, WLCalCS.END_7) | \
    #                 (WLCalCS.END_1, WLCalCS.END_6) | \
    #                 (WLCalCS.END_2, WLCalCS.END_6) | \
    #                 (WLCalCS.END_3, WLCalCS.END_6) | \
    #                 (WLCalCS.END_4, WLCalCS.END_6) | \
    #                 (WLCalCS.END_5, WLCalCS.END_6) | \
    #                 (WLCalCS.END_1, WLCalCS.END_5) | \
    #                 (WLCalCS.END_2, WLCalCS.END_5) | \
    #                 (WLCalCS.END_3, WLCalCS.END_5) | \
    #                 (WLCalCS.END_4, WLCalCS.END_5) | \
    #                 (WLCalCS.END_1, WLCalCS.END_4) | \
    #                 (WLCalCS.END_2, WLCalCS.END_4) | \
    #                 (WLCalCS.END_3, WLCalCS.END_4) | \
    #                 (WLCalCS.END_1, WLCalCS.END_3) | \
    #                 (WLCalCS.END_2, WLCalCS.END_3) | \
    #                 (WLCalCS.END_1, WLCalCS.END_2):
    #             return other
    #         # First starts, second ends, first starts before second ends
    #         case (WLCalCS.START_2, WLCalCS.END_7) | \
    #                 (WLCalCS.START_3, WLCalCS.END_7) | \
    #                 (WLCalCS.START_3, WLCalCS.END_6) | \
    #                 (WLCalCS.START_4, WLCalCS.END_7) | \
    #                 (WLCalCS.START_4, WLCalCS.END_6) | \
    #                 (WLCalCS.START_4, WLCalCS.END_5) | \
    #                 (WLCalCS.START_5, WLCalCS.END_7) | \
    #                 (WLCalCS.START_5, WLCalCS.END_6) | \
    #                 (WLCalCS.START_5, WLCalCS.END_5) | \
    #                 (WLCalCS.START_5, WLCalCS.END_4) | \
    #                 (WLCalCS.START_6, WLCalCS.END_7) | \
    #                 (WLCalCS.START_6, WLCalCS.END_6) | \
    #                 (WLCalCS.START_6, WLCalCS.END_5) | \
    #                 (WLCalCS.START_6, WLCalCS.END_4) | \
    #                 (WLCalCS.START_6, WLCalCS.END_3) | \
    #                 (WLCalCS.START_7, WLCalCS.END_7) | \
    #                 (WLCalCS.START_7, WLCalCS.END_6) | \
    #                 (WLCalCS.START_7, WLCalCS.END_5) | \
    #                 (WLCalCS.START_7, WLCalCS.END_4) | \
    #                 (WLCalCS.START_7, WLCalCS.END_3) | \
    #                 (WLCalCS.START_7, WLCalCS.END_2):
    #             return WLCalCS.FULL
    #         # First ends, second starts, first ends after second starts
    #         case (WLCalCS.END_7, WLCalCS.START_2) | \
    #                 (WLCalCS.END_7, WLCalCS.START_3) | \
    #                 (WLCalCS.END_6, WLCalCS.START_3) | \
    #                 (WLCalCS.END_7, WLCalCS.START_4) | \
    #                 (WLCalCS.END_6, WLCalCS.START_4) | \
    #                 (WLCalCS.END_5, WLCalCS.START_4) | \
    #                 (WLCalCS.END_7, WLCalCS.START_5) | \
    #                 (WLCalCS.END_6, WLCalCS.START_5) | \
    #                 (WLCalCS.END_5, WLCalCS.START_5) | \
    #                 (WLCalCS.END_4, WLCalCS.START_5) | \
    #                 (WLCalCS.END_7, WLCalCS.START_6) | \
    #                 (WLCalCS.END_6, WLCalCS.START_6) | \
    #                 (WLCalCS.END_5, WLCalCS.START_6) | \
    #                 (WLCalCS.END_4, WLCalCS.START_6) | \
    #                 (WLCalCS.END_3, WLCalCS.START_6) | \
    #                 (WLCalCS.END_7, WLCalCS.START_7) | \
    #                 (WLCalCS.END_6, WLCalCS.START_7) | \
    #                 (WLCalCS.END_5, WLCalCS.START_7) | \
    #                 (WLCalCS.END_4, WLCalCS.START_7) | \
    #                 (WLCalCS.END_3, WLCalCS.START_7) | \
    #                 (WLCalCS.END_2, WLCalCS.START_7):
    #             return WLCalCS.FULL
    #         case _:
    #             return WLCalCS.FUZZY

    pass


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

    def render(self) -> TextualRenderResult:
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


class MeTaskingTuiCommands(Provider):

    async def search(self, query: str) -> Hits:
        app: "MeTaskingTui" = self.app  # type: ignore
        matcher = self.matcher(query)

        actions: Iterable[tuple[str, Callable[[], Any], str, bool]] = (
            (
                "Refresh",
                app.action_refresh,
                "Refresh logs",
                True,
            ),
            (
                "Delete",
                app.action_delete,
                "Delete active log",
                False,
            ),
            (
                "Edit",
                app.action_edit,
                "Edit active log",
                False,
            ),
            (
                "Next",
                app.action_next,
                "Stop active log and start new one",
                False,
            ),
            (
                "Pause",
                app.action_pause,
                "Pause active log",
                False,
            ),
            (
                "Resume",
                app.action_resume,
                "Resume last stopped log",
                False,
            ),
            (
                "Start",
                app.action_start,
                "Start new log and pause active one",
                False,
            ),
            (
                "Stop",
                app.action_stop,
                "Stop active log",
                False,
            ),
            (
                "Stop all",
                app.action_stop_all,
                "Stop all logs",
                False,
            ),
            (
                "Load more",
                app.action_more,
                "Load more stopped logs",
                True,
            ),
        )

        for name, runnable, help_text, read_only in actions:
            if app._read_only_mode and not read_only:
                continue
            match = matcher.match(name)
            if match == 0:
                continue
            yield Hit(
                match,
                matcher.highlight(name),
                runnable,
                help=help_text,
            )


class MeTaskingTui(App):

    CSS = """
    Tabs {
        dock: top;
    }

    .heading {
        text-style: bold;
        border-bottom: solid darkgray;
    }
    .log-id {
        text-style: bold;
    }
    .log-name {
        text-style: bold;
    }

    .no-logs {
        display: none;
    }
    .container-logs-wrapper-empty .no-logs {
        display: block;
    }

    .container-logs-wrapper, .container-logs {
        height: auto;
    }

    .container-top {
        padding-left: 1;
        padding-right: 1;
    }

    #container-logs {
        height: 100%;
        display: none;
    }

    #container-calendar {
        display: none;
    }

    .tab-selected {
        display: block !important;
    }

    #container-active-log,
    #container-non-stopped-logs,
    #container-stopped-logs {
        height: auto;
    }

    #container-active-log {
        border: dashed yellow;
    }
    #container-active-log-inner {
    }
    #container-non-stopped-logs {
        border: solid green;
    }
    #container-non-stopped-logs-inner {
    }
    #container-stopped-logs {
        border: solid brown;
    }
    #container-stopped-logs-inner {
    }
    """

    _server: str
    _read_only_mode: bool

    COMMANDS = {
        SystemCommands,
        MeTaskingTuiCommands,
    }

    def __init__(self, server: str, read_only_mode: bool) -> None:
        self._server = server
        self._read_only_mode = read_only_mode
        super().__init__()

    def on_mount(self) -> None:
        self.query_one(Tabs).focus()
        self.call_after_refresh(self.action_refresh)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab is None:
            self.query_one("#container-calendar").remove_class("tab-selected")
            self.query_one("#container-logs").remove_class("tab-selected")
        elif event.tab.id == "tab-logs":
            self.query_one("#container-calendar").remove_class("tab-selected")
            self.query_one("#container-logs").add_class("tab-selected")
        elif event.tab.id == "tab-calendar":
            self.query_one("#container-logs").remove_class("tab-selected")
            self.query_one("#container-calendar").add_class("tab-selected")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        yield Tabs(
            Tab("Logs", id="tab-logs"),
            Tab("Calendar", id="tab-calendar"),
        )

        with Container(
            id="container-logs",
            # classes="container-top",
        ):
            with Container(
                id="container-active-log",
                classes="container-top",
            ):
                yield Static("Active log(s)", classes="heading")
                yield LogList(
                    server=self._server,
                    only_active=True,
                    reload_all_logs=self.action_refresh,
                    read_only_mode=self._read_only_mode,
                    id="container-active-log-inner",
                )

            with AutoLoadScrollableContainer(
                scroll_end_callback=self.action_more
            ):
                with Container(
                    id="container-non-stopped-logs",
                    classes="container-top",
                ):
                    yield Static(
                        "Non-stopped log(s)",
                        classes="heading",
                    )
                    yield LogList(
                        server=self._server,
                        only_active=False,
                        filters={"stopped": False},
                        reload_all_logs=self.action_refresh,
                        read_only_mode=self._read_only_mode,
                        id="container-non-stopped-logs-inner",
                    )

                with Container(
                    id="container-stopped-logs",
                    classes="container-top",
                ):
                    yield Static(
                        "Stopped log(s)",
                        classes="heading",
                    )
                    yield LogList(
                        server=self._server,
                        only_active=False,
                        filters={"stopped": True},
                        reload_all_logs=self.action_refresh,
                        read_only_mode=self._read_only_mode,
                        id="container-stopped-logs-inner",
                    )

        yield WorkLogCalendar(
            server=self._server,
            id="container-calendar",
            # classes="container-top",
        )

    def action_refresh(self) -> None:
        """An action to refresh data."""
        for log_list in self.query(LogList).results():
            log_list.reload_logs()
        for calendar in self.query(WorkLogCalendar).results():
            calendar.refresh_data()

    @work(thread=True)
    def action_delete(self) -> None:
        """An action to delete active log."""
        delete(self._server, -1)
        self.call_after_refresh(self.action_refresh)

    def action_edit(self) -> None:
        """An action to edit active log."""
        # TODO: Implement edit
        pass

    @work(thread=True)
    def action_next(self) -> None:
        """An action to stop active log and start new one."""
        next(self._server)
        self.call_after_refresh(self.action_refresh)

    @work(thread=True)
    def action_pause(self) -> None:
        """An action to pause active log."""
        pause_active(self._server)
        self.call_after_refresh(self.action_refresh)

    @work(thread=True)
    def action_resume(self) -> None:
        """An action to resume active log."""
        resume(self._server, -1)
        self.call_after_refresh(self.action_refresh)

    @work(thread=True)
    def action_start(self) -> None:
        """An action to start new log and pause active one."""
        start(self._server)
        self.call_after_refresh(self.action_refresh)

    @work(thread=True)
    def action_stop(self) -> None:
        """An action to stop active log."""
        stop_active(self._server)
        self.call_after_refresh(self.action_refresh)

    @work(thread=True)
    def action_stop_all(self) -> None:
        """An action to stop all logs."""
        stop_all(self._server)
        self.call_after_refresh(self.action_refresh)

    def action_more(self) -> None:
        """An action to load more stopped logs."""
        log_list: LogList = \
            self.query_one("#container-stopped-logs-inner")  # type: ignore
        log_list.load_more_logs()


def init_app(server: str, read_only_mode: bool) -> MeTaskingTui:
    if read_only_mode:
        class MeTaskingTuiReadOnly(MeTaskingTui):
            BINDINGS = [
                Binding("r", "refresh", "Refresh"),
            ]

        return MeTaskingTuiReadOnly(server, True)
    else:
        class MeTaskingTuiWritable(MeTaskingTui):
            BINDINGS = [
                # Binding("d", "toggle_dark", "Toggle dark mode"),
                Binding("ctrl+r", "refresh", "Refresh"),
                # Delete active log
                # Binding("alt+d", "delete", "Delete"),
                # Edit active log
                # Binding("alt+e", "edit", "Edit"),
                # Stop active log and start new one
                Binding("alt+n", "next", "Next"),
                # Pause active log
                Binding("alt+p", "pause", "Pause"),
                # Resume last stopped log
                Binding("alt+l", "resume", "Resume"),
                # Start new log and pause active one
                Binding("alt+s", "start", "Start"),
                # Stop active log
                Binding("alt+w", "stop", "Stop"),
                # Stop all logs
                # Binding("alt+e", "stop_all", "Stop all"),
                # Load more stopped logs
                # Binding("alt+m", "more", "Load more"),
            ]

        return MeTaskingTuiWritable(server, False)
