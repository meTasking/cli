from typing import Any, Callable, Mapping, Iterable
from datetime import datetime

from textual import work
from textual.app import App, ComposeResult
from textual._system_commands import SystemCommands
from textual.command import Hit, Hits, Provider
from textual.binding import Binding
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.events import Key
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Static

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

    WorkLog .log-date {
        text-opacity: 80%;
        width: auto;
        height: 1;
    }

    WorkLog .log-time {
        text-opacity: 80%;
        width: auto;
        height: 1;
    }

    WorkLog .log-description {
        content-align: center middle;
        text-opacity: 80%;
        width: auto;
        height: 3;
    }

    WorkLog .log-middle {
        content-align: center middle;
        width: auto;
        height: 5;
        border-left: solid darkgray;
        border-right: hidden darkgray;
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
        self.active = False

        if len(self._log['records']) > 0:
            log_start = datetime.fromisoformat(
                self._log['records'][0]['start']
            )
            log_end_str = self._log['records'][-1]['end']

            self.start_date = log_start.strftime("%Y-%m-%d")
            self.start_time = log_start.strftime("%H:%M:%S")

            if log_end_str is not None:
                log_end = datetime.fromisoformat(log_end_str)
                self.end_date = log_end.strftime("%Y-%m-%d")
                self.end_time = log_end.strftime("%H:%M:%S")
            else:
                self.end_date = self.start_date
                self.active = True

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

    def _generate_identifiers(self) -> Iterable[Widget]:
        yield EditableStatic(
            self._log['category']['name'] if self._log['category'] else None,
            fallback_text="Default",
            save_callback=self.save_category,
            classes="log-category"
        )
        yield EditableStatic(
            self._log['task']['name'] if self._log['task'] else None,
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

    def _generate_middle(self) -> Iterable[Widget]:
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

    def _generate_buttons(self) -> Iterable[Widget]:
        if self._read_only_mode:
            return

        if not self._log['stopped']:
            yield Button("Stop", name="stop", classes="log-button log-stop")

        if self.active:
            yield Button("Pause", name="pause", classes="log-button log-pause")
        else:
            yield Button(
                "Resume",
                name="resume",
                classes="log-button log-resume"
            )

        # yield Button("Edit", name="edit", classes="log-button log-edit")
        yield Button("Delete", name="delete", classes="log-button log-delete")

    def compose(self) -> ComposeResult:
        yield Container(
            *self._generate_identifiers(),
            classes="log-identifiers",
        )
        yield Container(
            *self._generate_middle(),
            classes="log-middle",
        )

        yield Horizontal(
            *self._generate_buttons(),
            classes="log-buttons",
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
        self.call_after_refresh(self.action_refresh)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        heading_active_log = Static("Active log(s)", classes="heading")
        yield Container(
            heading_active_log,
            LogList(
                server=self._server,
                only_active=True,
                reload_all_logs=self.action_refresh,
                read_only_mode=self._read_only_mode,
                id="container-active-log-inner",
            ),
            id="container-active-log",
            classes="container-top",
        )

        heading_non_stopped_logs = Static(
            "Non-stopped log(s)",
            classes="heading",
        )
        non_stopped_logs_container = Container(
            heading_non_stopped_logs,
            LogList(
                server=self._server,
                only_active=False,
                filters={"stopped": False},
                reload_all_logs=self.action_refresh,
                read_only_mode=self._read_only_mode,
                id="container-non-stopped-logs-inner",
            ),
            id="container-non-stopped-logs",
            classes="container-top",
        )

        heading_stopped_logs = Static("Stopped log(s)", classes="heading")
        stopped_logs_container = Container(
            heading_stopped_logs,
            LogList(
                server=self._server,
                only_active=False,
                filters={"stopped": True},
                reload_all_logs=self.action_refresh,
                read_only_mode=self._read_only_mode,
                id="container-stopped-logs-inner",
            ),
            id="container-stopped-logs",
            classes="container-top",
        )

        yield AutoLoadScrollableContainer(
            non_stopped_logs_container,
            stopped_logs_container,
            scroll_end_callback=self.action_more
        )

    def action_refresh(self) -> None:
        """An action to refresh data."""
        for log_list in self.query(LogList).results():
            log_list.reload_logs()

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
