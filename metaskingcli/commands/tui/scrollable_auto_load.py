from typing import Callable, Any

from textual.containers import ScrollableContainer
from textual.widget import Widget


class AutoLoadScrollableContainer(ScrollableContainer):

    scroll_end_callback: Callable[[], Any] | None = None

    def __init__(
        self,
        *children: Widget,
        scroll_end_callback: Callable[[], Any] | None = None,
        **kwargs
    ) -> None:
        self.scroll_end_callback = scroll_end_callback
        super().__init__(*children, **kwargs)

    def on_mount(self) -> None:
        if self.check_on_the_edge():
            if self.scroll_end_callback is not None:
                self.call_after_refresh(self.scroll_end_callback)

    @property
    def scroll_y_edge(self) -> float:
        if self.max_scroll_y > 5:
            # We have enough space to scroll down
            return self.max_scroll_y - 5
        # elif self.content_size.height < self.size.height:
        #     # Content is smaller than the container
        #     # We are always on the edge
        #     return -1
        # else:
        #     # Content is bigger than the container but only a little bit
        #     # We are always on the edge

        # We are always on the edge
        return -1

    def check_on_the_edge(self) -> bool:
        edge = self.scroll_y_edge
        return self.scroll_y > edge

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        edge = self.scroll_y_edge
        if old_value <= edge and new_value > edge:
            if self.scroll_end_callback is not None:
                self.call_after_refresh(self.scroll_end_callback)

        return super().watch_scroll_y(old_value, new_value)
