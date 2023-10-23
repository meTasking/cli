from typing import Iterable
from datetime import datetime, timedelta, date, time

from textual import work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Static, ProgressBar
from textual.widget import Widget

from metaskingcli.utils import split_hours
from metaskingcli.api.log import (
    list_all,
)


HOUR_SECONDS = 60.0 * 60.0


def _get_month_start(d: date) -> date:
    return date(d.year, d.month, 1)


class WorkLogReportDay(Widget):

    DEFAULT_CSS = """
    WorkLogReportDay {
        height: 1;
        width: 100%;
        color: darkcyan;
    }

    WorkLogReportDay .day-header {
        dock: left;
        width: 4;
        text-align: left;
    }

    WorkLogReportDay .day-progress, WorkLogReportDay .day-progress-limit {
        width: 1fr;
        padding-left: 1;
        padding-right: 1;
    }

    WorkLogReportDay .day-progress *, WorkLogReportDay .day-progress-limit * {
        width: 100%;
    }

    WorkLogReportDay .day-time {
        dock: right;
        width: 20;
        text-align: right;
    }
    """

    logs_server: str
    total: bool = False
    day: reactive[date | None] = reactive(None)
    # since: reactive[date | None] = reactive(None)
    # until: reactive[date | None] = reactive(None)

    _current: float | None = None
    # _total: float | None = None

    def __init__(
        self,
        server: str,
        total: bool = False,
        day: date | None = None,
        **kwargs
    ) -> None:
        self.logs_server = server
        super().__init__(**kwargs)
        self.total = total
        self.day = day

    def on_mount(self) -> None:
        self._refresh_data()

    def watch_total(self, old_value: bool, new_value: bool) -> None:
        if old_value == new_value:
            # This is called during initialization which is bad
            return

        self._current = None
        self.update_content()
        self._refresh_data()

    def watch_day(self, old_value: date, new_value: date) -> None:
        if old_value == new_value:
            # This is called during initialization which is bad
            return

        self._current = None
        self.update_content()
        self._refresh_data()

    # def watch_since(self, old_value: date, new_value: float) -> None:
    #     if old_value == new_value:
    #         # This is called during initialization which is bad
    #         return

    #     self._total = None
    #     self.refresh_data()

    # def watch_until(self, old_value: date, new_value: float) -> None:
    #     if old_value == new_value:
    #         # This is called during initialization which is bad
    #         return

    #     self._total = None
    #     self.refresh_data()

    def compose(self) -> ComposeResult:
        yield Static(
            classes="day-header",
        )

        with Horizontal():
            yield ProgressBar(
                show_bar=True,
                show_percentage=False,
                show_eta=False,
                classes="day-progress",
            )

            yield ProgressBar(
                show_bar=True,
                show_percentage=False,
                show_eta=False,
                classes="day-progress-limit",
            )

        yield Static(
            classes="day-time",
        )

    def update_content(self) -> None:
        day: Static = self.query_one(".day-header")  # type: ignore
        if self.total:
            day.update("SUM")
        elif self.day is None:
            day.update("--.")
        else:
            day.update(self.day.strftime("%d."))

        if self._current is None:
            target_time = None
            max_time = None
        elif self.total:
            target_time = 160.0
            max_time = 672.0
        else:
            target_time = 8.0
            max_time = 24.0

        progress: ProgressBar = self.query_one(".day-progress")  # type: ignore
        progress.update(
            progress=self._current or 0.0,
            total=target_time,
        )

        progress_limit: ProgressBar = self.query_one(  # type: ignore
            ".day-progress-limit"
        )
        progress_limit.update(
            progress=self._current or 0.0,
            total=max_time,
        )

        split_current = split_hours(self._current)

        time: Static = self.query_one(".day-time")  # type: ignore
        time.update(
            f"{split_current['hours']}h " +
            f"{split_current['minutes']}m " +
            f"{split_current['seconds']}s " +
            f"{split_current['milliseconds']}ms"
        )

    def _fetch_total(
        self,
        since: datetime,
        until: datetime
    ) -> Iterable[float]:
        total = 0.0

        for log in list_all(
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
                spent_time = end_time - start_time
                total += spent_time.total_seconds() / HOUR_SECONDS
                yield total
        yield total

    def refresh_data(self) -> None:
        self._current = None
        self.update_content()
        self._refresh_data()

    @work(thread=True, exclusive=True)
    def _refresh_data(self) -> None:
        if self.day is None:
            return

        if self.total:
            day_since = datetime.combine(
                date(self.day.year, self.day.month, 1),
                time.min
            )
            day_until = datetime.combine(
                date(self.day.year, self.day.month + 1, 1) - timedelta(days=1),
                time.max
            )
        else:
            day_since = datetime.combine(self.day, time.min)
            day_until = datetime.combine(self.day, time.max)

        for current in self._fetch_total(day_since, day_until):
            self._current = current
            self.call_after_refresh(self.update_content)

        # if self.since is None or self.until is None:
        #     total = None
        # else:
        #     month_since = datetime.combine(self.since, time.min)
        #     month_until = datetime.combine(self.until, time.max)
        #     total = self._fetch_total(month_since, month_until)

        # self._total = total


class WorkLogReport(ScrollableContainer):

    DEFAULT_CSS = """
    WorkLogReport {
        height: auto;
        width: 100%;
    }

    WorkLogReport .container-report-month {
        height: auto;
        width: 100%;
    }

    WorkLogReport .container-report-header {
        height: 3;
        width: 100%;
    }

    WorkLogReport .report-button-previous {
        dock: left;
    }

    WorkLogReport .report-button-next {
        dock: right;
    }

    WorkLogReport .report-date-heading {
        content-align: center middle;
        height: 3;
        width: 100%;
    }
    """

    logs_server: str
    month_start: reactive[date] = reactive(
        lambda: _get_month_start(date.today())
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

    @property
    def month_end(self) -> date:
        return date(
            self.month_start.year,
            self.month_start.month + 1,
            1,
        ) - timedelta(days=1)

    def watch_month_start(self, old_value: date, new_value: date) -> None:
        if old_value == new_value:
            # This is called during initialization which is bad
            return

        self.update_content()

    def update_content(self) -> None:
        heading: Static = self.query_one(
            ".report-date-heading"
        )  # type: ignore
        heading.update(
            f"{self.month_start.strftime('%Y-%m-%d')} - " +
            f"{self.month_end.strftime('%Y-%m-%d')}"
        )

        curr_month = self.month_start.month
        for i in range(31):
            day: WorkLogReportDay = self.query_one(  # type: ignore
                f".container-report-day-{i+1}"
            )
            target_day = self.month_start + timedelta(days=i)
            if target_day.month != curr_month:
                day.display = False
                day.day = None
            else:
                day.day = target_day
                day.display = True

        total: WorkLogReportDay = self.query_one(  # type: ignore
            ".container-report-day-total"
        )
        total.day = self.month_start

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""

        button_name = event.button.name
        if button_name == "previous":
            self.month_start = date(
                self.month_start.year,
                self.month_start.month - 1,
                1,
            )
        elif button_name == "next":
            self.month_start = date(
                self.month_start.year,
                self.month_start.month + 1,
                1,
            )

    def compose(self) -> ComposeResult:
        with Container(classes="container-report-header"):
            yield Button(
                "<",
                name="previous",
                classes="report-button-previous",
            )
            yield Static(
                classes="report-date-heading",
            )
            yield Button(
                ">",
                name="next",
                classes="report-button-next",
            )

        with Container(classes="container-report-month"):
            for i in range(31):
                yield WorkLogReportDay(
                    self.logs_server,
                    classes=(
                        "container-report-day " +
                        "container-report-day-" + str(i+1)
                    ),
                )
            yield WorkLogReportDay(
                self.logs_server,
                total=True,
                classes="container-report-day container-report-day-total",
            )

    def refresh_data(self) -> None:
        for day_widget in self.query(WorkLogReportDay).results():
            day_widget.refresh_data()
