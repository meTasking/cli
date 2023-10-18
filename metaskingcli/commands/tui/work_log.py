from typing import Any, Callable
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Static

from metaskingcli.api.log import (
    stop,
    pause,
    resume,
    delete,
    update
)

from .range_bar import RangeBar
from .editable import EditableText


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
        text-style: bold;
    }

    WorkLog .log-name {
        min-height: 1;
        width: auto;
        color: green;
        text-style: bold;
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
            yield EditableText(
                (
                    self._log['category']['name']
                    if self._log['category'] else None
                ),
                fallback_text="Default",
                save_callback=self.save_category,
                classes="log-category"
            )
            yield EditableText(
                (
                    self._log['task']['name']
                    if self._log['task'] else None
                ),
                fallback_text="Default",
                save_callback=self.save_task,
                classes="log-task"
            )

            yield Static(str(self._log['id']), classes="log-id")
            yield EditableText(
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
                RangeBar(self.activity_ranges),
                classes="log-visualization"
            )

            date_str = self.start_date
            if self.start_date != self.end_date:
                date_str += " - " + self.end_date
            yield Static(date_str, classes="log-date")

            time_str = self.start_time + " - " + self.end_time
            yield Static(time_str, classes="log-time")

            yield EditableText(
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
