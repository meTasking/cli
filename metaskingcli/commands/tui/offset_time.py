from datetime import datetime, timedelta

from textual.app import RenderResult as TextualRenderResult
from textual.reactive import reactive
from textual.widget import Widget

from metaskingcli.utils import split_hours


class OffsetTime(Widget, can_focus=False):
    """Shows current time offset by timedelta and the offset itself."""

    DEFAULT_CSS = """
    OffsetTime {
        content-align: right middle;
        width: 16;
        height: 2;
        padding-left: 1;
        padding-right: 1;
    }
    """

    time_offset: reactive[timedelta] = reactive[timedelta](timedelta)
    """Time offset to apply to current time."""

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.auto_refresh = 0.5

    def render(self) -> TextualRenderResult:

        time = datetime.now() + self.time_offset

        hours = self.time_offset.total_seconds() / 3600
        components = split_hours(abs(hours))

        return (
            f"{'-' if hours < 0 else '+'}" +
            f"{components['hours']}:" +
            f"{components['minutes']}:" +
            f"{components['seconds']}." +
            f"{components['milliseconds']}\n" +
            f"{time.strftime('%H:%M:%S.%f')[:-3]}"
        )
