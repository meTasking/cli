from typing import Any, Callable, Mapping, Iterable

from textual import work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Container
from textual.widgets import Static

from metaskingcli.api.log import (
    get_active,
    list_page,
)

from .work_log import WorkLog


class LogList(ScrollableContainer):

    DEFAULT_CSS = """
    .no-logs {
        display: none;
    }
    .container-logs-wrapper-empty .no-logs {
        display: block;
    }

    .container-logs-wrapper, .container-logs {
        height: auto;
    }
    """

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
        at_offset: int,
        reached_end: bool,
        logs: list[dict[str, Any]]
    ) -> None:
        if at_offset != self.logs_offset:
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

        # Check if enough logs were loaded
        self.call_after_refresh(self.check_load_more_logs)

    @work(exclusive=True, thread=True)
    def load_more_logs(self) -> None:
        reached_end = self.logs_reached_end
        offset = self.logs_offset

        if reached_end:
            return

        limit = 20

        if self.logs_only_active:
            logs = []
            active_log = get_active(self.logs_server)
            if active_log is not None:
                logs.append(active_log)
            reached_end = True
        else:
            logs = list_page(
                self.logs_server,
                offset=self.logs_offset,
                limit=limit,
                **self.logs_filters
            )
            if len(logs) < limit:
                reached_end = True

        self.call_after_refresh(self._add_logs, offset, reached_end, logs)

    def compose(self) -> ComposeResult:
        yield Static("No logs", classes="no-logs")
        yield Container(classes="container-logs")

    @property
    def scroll_y_edge(self) -> float:
        if self.max_scroll_y > 5:
            return self.max_scroll_y - 5
        return self.max_scroll_y

    def check_load_more_logs(self) -> None:
        edge = self.scroll_y_edge
        if self.scroll_y > edge:
            self.load_more_logs()

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        edge = self.scroll_y_edge
        if old_value <= edge and new_value > edge:
            self.load_more_logs()

        return super().watch_scroll_y(old_value, new_value)
