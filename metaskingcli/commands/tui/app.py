from typing import Any, Callable, Iterable
from functools import partial
from datetime import timedelta

from textual.app import App, ComposeResult
from textual._system_commands import SystemCommands
from textual.command import Hit, Hits, Provider
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import (
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
    Button,
)

from metaskingcli.api.log import (
    stop_all,
    stop_active,
    start,
    next,
    pause_active,
    resume,
    delete,
)

from .editable import EditableText
from .slider import Slider
from .offset_time import OffsetTime
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
    .heading {
        text-style: bold;
        border-bottom: solid darkgray;
    }

    #container-header {
        width: 100%;
        height: 4;
        padding-left: 1;
        padding-right: 1;
        border-bottom: solid darkgray;
    }

    #container-modifiers {
        width: 1fr;
        height: 3;
    }

    #container-filter-category {
        width: 1fr;
        height: 1;
    }

    #text-filter-category {
        content-align: left middle;
        width: 13;
        height: 1;
    }

    .filter-category {
        height: 1;
        width: auto;
        color: cyan;
    }

    #container-filter-task {
        width: 1fr;
        height: 1;
    }

    #text-filter-task {
        content-align: left middle;
        width: 13;
        height: 1;
    }

    .filter-task {
        height: 1;
        width: auto;
        color: yellow;
    }

    #container-time-adjust {
        width: 1fr;
        height: 1;
    }

    #text-time-adjust {
        content-align: left middle;
        width: 13;
        height: 1;
    }

    #slider-time-adjust {
        content-align: center middle;
        width: 1fr;
        height: 1;
    }

    #container-tabs {
        width: 100%;
        height: 1fr;
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

    time_adjust: timedelta
    category: str | None = None
    task: str | None = None

    @property
    def time_adjust_params(self) -> dict[str, Any]:
        return {
            'adjust-time': self.time_adjust.total_seconds(),
        }

    @property
    def filter_params(self) -> dict[str, Any]:
        params = {}
        if self.category is not None:
            params['category'] = self.category
        if self.task is not None:
            params['task'] = self.task
        return params

    COMMANDS = {
        SystemCommands,
        MeTaskingTuiCommands,
    }

    def __init__(
        self,
        server: str,
        read_only_mode: bool,
        category: str | None = None,
        task: str | None = None,
    ) -> None:
        self._server = server
        self._read_only_mode = read_only_mode
        self.time_adjust = timedelta()
        self.category = category
        self.task = task
        super().__init__()

    # def on_mount(self) -> None:
    #     self.call_after_refresh(self.action_refresh)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        with Horizontal(id="container-header"):
            with Container(id="container-modifiers"):
                with Horizontal(id="container-time-adjust"):
                    yield Static("Time adjust: ", id="text-time-adjust")

                    slider = Slider(progress=0.5, id="slider-time-adjust")
                    yield slider
                    self.watch(
                        slider,
                        "percentage",
                        self.time_adjust_update,
                        init=False,
                    )
                with Horizontal(id="container-filter-category"):
                    yield Static("Category: ", id="text-filter-category")

                    yield EditableText(
                        text=self.category,
                        fallback_text="Default",
                        save_callback=self.filter_category,
                        classes="filter-category"
                    )
                with Horizontal(id="container-filter-task"):
                    yield Static("Task: ", id="text-filter-task")

                    yield EditableText(
                        text=self.task,
                        fallback_text="Default",
                        save_callback=self.filter_task,
                        classes="filter-task"
                    )

            yield OffsetTime(id="label-time-adjust")
            yield Button("Reset", name="reset-time-adjust")

        with TabbedContent(id="container-tabs"):
            with TabPane("Logs", name="logs", id="tab-logs"):
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
                        scroll_end_callback=partial(
                            self.call_after_refresh,
                            self.scroll_end_callback,
                        ),
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
                                paging=False,
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

            with TabPane("Calendar", name="calendar", id="tab-calendar"):
                yield WorkLogCalendar(
                    server=self._server,
                    id="container-calendar",
                    # classes="container-top",
                )

            with TabPane("Report", name="report", id="tab-report"):
                yield WorkLogReport(
                    server=self._server,
                    id="container-report",
                    # classes="container-top",
                )

    def filter_category(self, category: str | None) -> None:
        self.category = category
        self.call_after_refresh(self.action_refresh)

    def filter_task(self, task: str | None) -> None:
        self.task = task
        self.call_after_refresh(self.action_refresh)

    def time_adjust_update(self, percentage: float | None) -> None:
        if percentage is None:
            return

        sign = 1 if percentage >= 0.5 else -1

        offset = percentage - 0.5  # -0.5 ~ 0.5
        offset *= 60  # -30 ~ 30
        offset += 5 * sign  # -35 ~ -5, 5 ~ 35
        seconds = offset ** 3  # -42875 ~ -125, 125 ~ 42875 (exponential)
        seconds -= 125 * sign  # -42750 ~ 42750 (exponential)

        time_adjust = timedelta(seconds=seconds)
        self.time_adjust = time_adjust

        label: OffsetTime = self.query_one(
            "#label-time-adjust"
        )  # type: ignore
        label.time_offset = time_adjust

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        button_name = event.button.name
        if button_name == "reset-time-adjust":
            slider: Slider = self.query_one(
                "#slider-time-adjust"
            )  # type: ignore
            slider.percentage = 0.5

    def action_refresh(self) -> None:
        """An action to refresh data."""
        match self.query_one(TabbedContent).active:
            case "tab-logs":
                for log_list in self.query(LogList).results():
                    log_list.reload_logs()
            case "tab-calendar":
                self.query_one(WorkLogCalendar).refresh_data()
            case "tab-report":
                self.query_one(WorkLogReport).refresh_data()

    async def action_delete(self) -> None:
        """An action to delete active log."""
        await delete(self._server, -1)
        self.call_after_refresh(self.action_refresh)

    async def action_edit(self) -> None:
        """An action to edit active log."""
        # TODO: Implement edit
        pass

    async def action_next(self) -> None:
        """An action to stop active log and start new one."""
        await next(
            self._server,
            {
                "create-category": "true",
                "create-task": "true",
                **self.time_adjust_params,
            },
            **self.filter_params
        )
        self.call_after_refresh(self.action_refresh)

    async def action_pause(self) -> None:
        """An action to pause active log."""
        await pause_active(self._server, **self.time_adjust_params)
        self.call_after_refresh(self.action_refresh)

    async def action_resume(self) -> None:
        """An action to resume active log."""
        await resume(self._server, -1, **self.time_adjust_params)
        self.call_after_refresh(self.action_refresh)

    async def action_start(self) -> None:
        """An action to start new log and pause active one."""
        await start(
            self._server,
            {
                "create-category": "true",
                "create-task": "true",
                **self.time_adjust_params,
            },
            **self.filter_params
        )
        self.call_after_refresh(self.action_refresh)

    async def action_stop(self) -> None:
        """An action to stop active log."""
        await stop_active(self._server, **self.time_adjust_params)
        self.call_after_refresh(self.action_refresh)

    async def action_stop_all(self) -> None:
        """An action to stop all logs."""
        await stop_all(
            self._server,
            **self.time_adjust_params,
            **self.filter_params
        )
        self.call_after_refresh(self.action_refresh)

    def action_more(self) -> None:
        """An action to load more stopped logs."""
        log_list: LogList = \
            self.query_one("#container-stopped-logs-inner")  # type: ignore
        log_list.load_more_logs()

    def scroll_end_callback(self) -> None:
        """A callback called when the scroll reaches the end."""
        # Load more stopped logs as long as the scroll is on the edge
        log_list: LogList = \
            self.query_one("#container-stopped-logs-inner")  # type: ignore
        # await log_list.load_more_logs().wait()
        log_list.load_more_logs()

        # scroll_container = self.query_one(AutoLoadScrollableContainer)
        # if scroll_container.check_on_the_edge() and \
        #         not log_list.logs_reached_end:
        #     self.call_after_refresh(self.scroll_end_callback)


def init_app(
    server: str,
    read_only_mode: bool,
    category: str | None,
    task: str | None
) -> MeTaskingTui:
    if read_only_mode:
        class MeTaskingTuiReadOnly(MeTaskingTui):
            BINDINGS = [
                Binding("r", "refresh", "Refresh"),
            ]

        return MeTaskingTuiReadOnly(server, True, category, task)
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

        return MeTaskingTuiWritable(server, False, category, task)
