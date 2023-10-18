from typing import Callable

from textual.containers import ScrollableContainer
from textual.widget import Widget


class AutoLoadScrollableContainer(ScrollableContainer):

    scroll_end_callback: Callable[[], None] | None = None

    def __init__(
        self,
        *children: Widget,
        scroll_end_callback: Callable[[], None] | None = None,
        **kwargs
    ) -> None:
        self.scroll_end_callback = scroll_end_callback
        super().__init__(*children, **kwargs)

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        edge = self.max_scroll_y - 5
        if old_value <= edge and new_value > edge:
            if self.scroll_end_callback is not None:
                self.call_after_refresh(self.scroll_end_callback)

        return super().watch_scroll_y(old_value, new_value)
