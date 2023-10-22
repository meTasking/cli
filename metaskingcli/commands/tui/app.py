from typing import Any, Callable, Iterable

from textual import work
from textual.app import App, ComposeResult
from textual._system_commands import SystemCommands
from textual.command import Hit, Hits, Provider
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, Static, Tabs, Tab

from metaskingcli.api.log import (
    stop_all,
    stop_active,
    start,
    next,
    pause_active,
    resume,
    delete,
)

from .scrollable_auto_load import AutoLoadScrollableContainer
from .work_log_list import LogList
from .calendar import WorkLogCalendar
from .report import WorkLogReport


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

    TITLE = "MeTasking TUI"

    CSS = """
    #header {
        dock: top;
        height: auto;
        width: 100%;
    }

    .heading {
        text-style: bold;
        border-bottom: solid darkgray;
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

    #container-report {
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
            self.query_one("#container-report").remove_class("tab-selected")
            self.query_one("#container-calendar").remove_class("tab-selected")
            self.query_one("#container-logs").remove_class("tab-selected")
        elif event.tab.id == "tab-logs":
            self.query_one("#container-report").remove_class("tab-selected")
            self.query_one("#container-calendar").remove_class("tab-selected")
            self.query_one("#container-logs").add_class("tab-selected")
        elif event.tab.id == "tab-calendar":
            self.query_one("#container-report").remove_class("tab-selected")
            self.query_one("#container-calendar").add_class("tab-selected")
            self.query_one("#container-logs").remove_class("tab-selected")
        elif event.tab.id == "tab-report":
            self.query_one("#container-report").add_class("tab-selected")
            self.query_one("#container-calendar").remove_class("tab-selected")
            self.query_one("#container-logs").remove_class("tab-selected")

    def compose(self) -> ComposeResult:
        with Container(id="header"):
            yield Header(show_clock=True)
            yield Tabs(
                Tab("Logs", id="tab-logs"),
                Tab("Calendar", id="tab-calendar"),
                Tab("Report", id="tab-report"),
            )

        yield Footer()

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

        yield WorkLogReport(
            server=self._server,
            id="container-report",
            # classes="container-top",
        )

    def action_refresh(self) -> None:
        """An action to refresh data."""
        for log_list in self.query(LogList).results():
            log_list.reload_logs()
        for calendar in self.query(WorkLogCalendar).results():
            calendar.refresh_data()
        for report in self.query(WorkLogReport).results():
            report.refresh_data()

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
