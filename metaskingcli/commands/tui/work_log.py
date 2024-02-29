from typing import TYPE_CHECKING, Any, Callable
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Static, LoadingIndicator

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


class WorkLog(Widget):
    """A widget that displays a work log."""

    DEFAULT_CSS = """
    WorkLog {
        layout: horizontal;
        background: $boost;
        height: 7;
        margin: 1;
        min-width: 125;
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

    WorkLog .log-menu {
        background: darkgray;
        width: 5;
        max-width: 5;
    }
    """

    _refresh_app: Callable[[], None]
    _logs_server: str
    _read_only_mode: bool
    _log: reactive[dict[str, Any] | None] = reactive(None)
    _menu_visible: reactive[bool] = reactive(False)

    _is_mounted: bool = False

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
        log: dict[str, Any] | None = None,
        read_only_mode: bool = False,
        **kwargs
    ) -> None:
        self._refresh_app = refresh_app
        self._logs_server = logs_server
        self._read_only_mode = read_only_mode

        super().__init__(**kwargs)

        self._log = log
        self.watch__log(log)

    def on_mount(self) -> None:
        self._is_mounted = True
        self.call_after_refresh(self._update_content)

    def watch__menu_visible(self, visible: bool) -> None:
        self._update_content()

    def watch__log(self, log: dict[str, Any] | None) -> None:
        self.start_date = "No records"
        self.end_date = "No records"
        self.start_time = "--:--:--"
        self.end_time = "--:--:--"
        self.activity_ranges = []
        self.active = False

        if log is None or len(log['records']) == 0:
            self._update_content()
            return

        log_start = datetime.fromisoformat(
            log['records'][0]['start']
        )

        self.start_date = log_start.strftime("%Y-%m-%d")
        self.start_time = log_start.strftime("%H:%M:%S")

        curr_time = datetime.now()
        log_end_str = log['records'][-1]['end']
        log_end = curr_time

        if log_end_str is not None:
            log_end = datetime.fromisoformat(log_end_str)
            self.end_date = log_end.strftime("%Y-%m-%d")
            self.end_time = log_end.strftime("%H:%M:%S")
        else:
            self.end_date = self.start_date
            self.active = True

        log_end_real = log_end if log['stopped'] else curr_time

        duration = (log_end_real - log_start).total_seconds()

        def get_activity_range(
            record: dict[str, Any]
        ) -> tuple[float, float]:
            if duration == 0:
                return (0, 1)
            start_time = datetime.fromisoformat(record['start'])
            start = (start_time - log_start).total_seconds() / duration
            if record['end'] is None:
                return (start, 1)

            end_time = datetime.fromisoformat(record['end'])
            end = (end_time - log_start).total_seconds() / duration
            return (start, end)

        self.activity_ranges = list(map(
            get_activity_range,
            log['records'],
        ))

        self._update_content()

    @work()
    async def save_category(self, category: str | None) -> None:
        if self._log is None:
            return

        self._log = await update(
            self._logs_server,
            self._log['id'],
            create_category=True,
            category=category,
        )

    @work()
    async def save_task(self, task: str | None) -> None:
        if self._log is None:
            return

        self._log = await update(
            self._logs_server,
            self._log['id'],
            create_task=True,
            task=task,
        )

    @work()
    async def save_name(self, name: str | None) -> None:
        if self._log is None:
            return

        self._log = await update(
            self._logs_server,
            self._log['id'],
            name=name,
        )

    @work()
    async def save_description(self, description: str | None) -> None:
        if self._log is None:
            return

        self._log = await update(
            self._logs_server,
            self._log['id'],
            description=description,
        )

    @work()
    async def save_flags(self, flags: str | None) -> None:
        if self._log is None:
            return

        self._log = await update(
            self._logs_server,
            self._log['id'],
            flags=(
                flags.split(',')
                if flags is not None
                else []
            ),
        )

    def _update_content(self) -> None:
        if not self._is_mounted:
            return

        log_category: EditableText = self.query_one(  # type: ignore
            ".log-category"
        )
        log_category.update_text(
            self._log['category']['name']
            if self._log is not None and self._log['category']
            else None
        )

        log_task: EditableText = self.query_one(".log-task")  # type: ignore
        log_task.update_text(
            self._log['task']['name']
            if self._log is not None and self._log['task']
            else None
        )

        log_id: Static = self.query_one(".log-id")  # type: ignore
        log_id.update(
            str(self._log['id'])
            if self._log is not None
            else "---"
        )

        log_name: EditableText = self.query_one(".log-name")  # type: ignore
        log_name.update_text(
            self._log['name']
            if self._log is not None
            else None
        )

        log_flags: EditableText = self.query_one(".log-flags")  # type: ignore
        log_flags.update_text(
            ','.join(self._log['flags'])
            if self._log is not None
            else None
        )

        date_str = self.start_date
        if self.start_date != self.end_date:
            date_str += " - " + self.end_date
        log_date: Static = self.query_one(".log-date")  # type: ignore
        log_date.update(date_str)

        time_str = self.start_time + " - " + self.end_time
        log_time: Static = self.query_one(".log-time")  # type: ignore
        log_time.update(time_str)

        log_description: EditableText = self.query_one(  # type: ignore
            ".log-description"
        )
        log_description.update_text(
            self._log['description']
            if self._log is not None
            else None
        )

        log_visualization: Static = self.query_one(  # type: ignore
            ".log-visualization"
        )
        log_visualization.update(
            RangeBar(self.activity_ranges)
        )

        if self._read_only_mode or self._log is None:
            buttons = self.query(".log-button")
            for button in buttons.nodes:
                button.display = False
        else:
            button_pause: Button = self.query_one(".log-pause")  # type: ignore
            button_resume: Button = self.query_one(
                ".log-resume"
            )  # type: ignore
            button_stop: Button = self.query_one(".log-stop")  # type: ignore
            button_clone: Button = self.query_one(".log-clone")  # type: ignore
            button_fill: Button = self.query_one(".log-fill")  # type: ignore
            button_delete: Button = self.query_one(
                ".log-delete"
            )  # type: ignore
            button_menu: Button = self.query_one(".log-menu")  # type: ignore

            button_pause.display = self.active
            button_resume.display = not self.active
            button_stop.display = (
                self._menu_visible and not self._log['stopped']
            )
            button_clone.display = self._menu_visible
            button_fill.display = self._menu_visible and not self.active
            button_delete.display = self._menu_visible
            button_menu.display = True
            button_menu.label = ">" if self._menu_visible else "<"

        self.query_one(LoadingIndicator).display = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(classes="-overlay")

        with Container():
            with Container(classes="log-identifiers"):
                yield EditableText(
                    fallback_text="Default",
                    save_callback=self.save_category,
                    classes="log-category"
                )
                yield EditableText(
                    fallback_text="Default",
                    save_callback=self.save_task,
                    classes="log-task"
                )

                yield Static(classes="log-id")
                yield EditableText(
                    fallback_text="---",
                    save_callback=self.save_name,
                    classes="log-name"
                )
                yield EditableText(
                    fallback_text="[]",
                    save_callback=self.save_flags,
                    classes="log-flags"
                )

            with Container(classes="log-middle"):
                yield Static(classes="log-date")
                yield Static(classes="log-time")

                yield EditableText(
                    fallback_text="No description",
                    save_callback=self.save_description,
                    classes="log-description"
                )

                yield Static(classes="log-visualization")

            with Horizontal(classes="log-buttons"):
                # if self._read_only_mode:
                #     return

                # if self.active:
                yield Button(
                    "Pause",
                    name="pause",
                    classes="log-button log-pause"
                )
                # else:
                yield Button(
                    "Resume",
                    name="resume",
                    classes="log-button log-resume"
                )

                # if not self._log['stopped']:
                yield Button(
                    "Stop",
                    name="stop",
                    classes="log-button log-stop"
                )

                yield Button(
                    "Clone",
                    name="clone",
                    classes="log-button log-clone"
                )

                # if not self.active:
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

                yield Button(
                    "<",
                    name="menu",
                    classes="log-button log-menu"
                )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        if self._log is None:
            return

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
        elif button_name == "menu":
            self._menu_visible = not self._menu_visible
            return

        self._refresh_app()
