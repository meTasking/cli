from typing import TYPE_CHECKING, Any, Callable
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
    update,
    update_active,
    start,
)

from .range_bar import RangeBar
from .editable import EditableText

if TYPE_CHECKING:
    from .app import MeTaskingTui


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

    WorkLog .log-clone {
        background: lightgreen;
    }

    WorkLog .log-fill {
        background: lightblue;
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

            curr_time = datetime.now()
            log_end_str = self._log['records'][-1]['end']
            log_end = curr_time

            if log_end_str is not None:
                log_end = datetime.fromisoformat(log_end_str)
                self.end_date = log_end.strftime("%Y-%m-%d")
                self.end_time = log_end.strftime("%H:%M:%S")
            else:
                self.end_date = self.start_date
                self.active = True

            log_end_real = log_end if self._log['stopped'] else curr_time

            duration = (log_end_real - log_start).total_seconds()

            def get_activity_range(
                record: dict[str, Any]
            ) -> tuple[float, float]:
                start_time = datetime.fromisoformat(record['start'])
                start = (start_time - log_start).total_seconds() / duration
                if record['end'] is None:
                    return (start, 1)

                end_time = datetime.fromisoformat(record['end'])
                end = (end_time - log_start).total_seconds() / duration
                return (start, end)

            self.activity_ranges = list(map(
                get_activity_range,
                self._log['records'],
            ))

        super().__init__(**kwargs)

    @work()
    async def save_category(self, category: str | None) -> None:
        await update(
            self._logs_server,
            self._log['id'],
            create_category=True,
            category=category,
        )

    @work()
    async def save_task(self, task: str | None) -> None:
        await update(
            self._logs_server,
            self._log['id'],
            create_task=True,
            task=task,
        )

    @work()
    async def save_name(self, name: str | None) -> None:
        await update(
            self._logs_server,
            self._log['id'],
            name=name,
        )

    @work()
    async def save_description(self, description: str | None) -> None:
        await update(
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

            yield Static(
                RangeBar(self.activity_ranges),
                classes="log-visualization"
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

            yield Button(
                "Clone",
                name="clone",
                classes="log-button log-clone"
            )

            if not self.active:
                yield Button(
                    "Fill",
                    name="fill",
                    classes="log-button log-fill"
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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        app: "MeTaskingTui" = self.app  # type: ignore

        button_name = event.button.name
        if button_name == "stop":
            await stop(
                self._logs_server,
                self._log['id'],
                **app.time_adjust_params,
            )
        elif button_name == "pause":
            await pause(
                self._logs_server,
                self._log['id'],
                **app.time_adjust_params,
            )
        elif button_name == "resume":
            await resume(
                self._logs_server,
                self._log['id'],
                **app.time_adjust_params
            )
        elif button_name == "clone":
            json_params: dict[str, Any] = {}
            if self._log['task'] is not None:
                json_params['task'] = self._log['task']['name']
            if self._log['category'] is not None:
                json_params['category'] = self._log['category']['name']
            if self._log['meta'] is not None:
                json_params['meta'] = self._log['meta']

            await start(
                self._logs_server,
                name=self._log['name'],
                description=self._log['description'],
                flags=self._log['flags'],
                params=app.time_adjust_params,
                **json_params,
            )
        elif button_name == "fill":
            params: dict[str, Any] = {
                'name': self._log['name'],
            }
            if self._log['task'] is not None:
                params['task'] = self._log['task']['name']
            if self._log['category'] is not None:
                params['category'] = self._log['category']['name']
            if self._log['description'] is not None:
                params['description'] = self._log['description']

            await update_active(
                self._logs_server,
                **params,
            )
        elif button_name == "edit":
            # TODO: Implement edit
            pass
        elif button_name == "delete":
            await delete(self._logs_server, self._log['id'])

        self._refresh_app()
