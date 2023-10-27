from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
from rich.style import Style, StyleType

from textual.app import RenderResult as TextualRenderResult
from textual.events import MouseMove, Click
from textual.reactive import reactive
from textual.widget import Widget


class SliderRenderable:
    """Thin horizontal bar with a portion highlighted.

    Args:
        percentage: The range to highlight.
        cursor_style: The style of the cursor of the bar.
        highlight_style: The style of the highlighted range of the bar.
        background_style: The style of the non-highlighted range(s) of the bar.
        width: The width of the bar, or ``None`` to fill available width.
    """

    def __init__(
        self,
        percentage: float = 0.0,
        cursor_style: StyleType = "white",
        highlight_style: StyleType = "magenta",
        background_style: StyleType = "grey37",
        clickable_ranges: dict[str, tuple[int, int]] | None = None,
        width: int | None = None,
    ) -> None:
        self.percentage = percentage
        self.cursor_style = cursor_style
        self.highlight_style = highlight_style
        self.background_style = background_style
        self.clickable_ranges = clickable_ranges or {}
        self.width = width

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        cursor_style = console.get_style(self.cursor_style)
        highlight_style = console.get_style(self.highlight_style)
        background_style = console.get_style(self.background_style)

        half_bar_right = "╸"
        half_bar_left = "╺"
        bar = "━"

        width = self.width or options.max_width
        center = self.percentage * width
        start = center - 0.5
        end = center + 0.5

        start = max(start, 0)
        end = min(end, width)

        output_bar = Text("", end="")

        if start == end == 0 or end < 0 or start > end:
            output_bar.append(Text(bar * width, style=highlight_style, end=""))
            yield output_bar
            return

        # Round start and end to nearest half
        start = round(start * 2) / 2
        end = round(end * 2) / 2

        # Check if we start/end on a number that rounds to a .5
        half_start = start - int(start) > 0
        half_end = end - int(end) > 0

        # Initial non-highlighted portion of bar
        output_bar.append(
            Text(bar * (int(start - 0.5)), style=highlight_style, end="")
        )
        if not half_start and start > 0:
            output_bar.append(Text(
                half_bar_right, style=highlight_style, end=""
            ))

        # The highlighted portion
        bar_width = int(end) - int(start)
        if half_start:
            output_bar.append(
                Text(
                    half_bar_left + bar * (bar_width - 1),
                    style=cursor_style,
                    end="",
                )
            )
        else:
            output_bar.append(Text(
                bar * bar_width, style=cursor_style, end=""
            ))
        if half_end:
            output_bar.append(Text(
                half_bar_right, style=cursor_style, end=""
            ))

        # The non-highlighted tail
        if not half_end and end - width != 0:
            output_bar.append(Text(
                half_bar_left, style=background_style, end=""
            ))
        output_bar.append(
            Text(
                bar * (int(width) - int(end) - 1),
                style=background_style,
                end="",
            )
        )

        # Fire actions when certain ranges are clicked (e.g. for tabs)
        for range_name, (start, end) in self.clickable_ranges.items():
            output_bar.apply_meta(
                {"@click": f"range_clicked('{range_name}')"}, start, end
            )

        yield output_bar


class Slider(Widget, can_focus=True):
    """Slider input."""

    COMPONENT_CLASSES = {"slider--slider"}
    """
    The bar sub-widget provides the component classes that follow.

    These component classes let you modify the foreground and background color
    of the bar in its different states.

    | Class | Description |
    | :- | :- |
    | `slider--slider` | Style of the bar (may be used to change the color). |
    """

    DEFAULT_CSS = """
    Slider {
        width: 32;
        height: 1;
    }

    Slider > .slider--slider {
        color: $warning;
        background: $foreground 10%;
    }

    Slider:focus {
        background: $boost;
    }
    """

    percentage: reactive[float] = reactive[float](0.0)
    """The percentage of progress that has been completed."""

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        progress: float = 0.0,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.percentage = progress

    def render(self) -> TextualRenderResult:
        """Render the bar with the correct portion filled."""

        bar_style = self.get_component_rich_style("slider--slider")
        return SliderRenderable(
            percentage=self.percentage,
            highlight_style=Style.from_color(bar_style.color),
            background_style=Style.from_color(bar_style.bgcolor),
        )

    def key_left(self) -> None:
        """Move the slider left."""
        self.percentage = max(self.percentage - 0.0005, 0.0)

    def key_ctrl_left(self) -> None:
        """Move the slider left."""
        self.percentage = max(self.percentage - 0.05, 0.0)

    def key_right(self) -> None:
        """Move the slider right."""
        self.percentage = min(self.percentage + 0.0005, 1.0)

    def key_ctrl_right(self) -> None:
        """Move the slider right."""
        self.percentage = min(self.percentage + 0.05, 1.0)

    def key_home(self) -> None:
        """Move the slider to the leftmost position."""
        self.percentage = 0.0

    def key_end(self) -> None:
        """Move the slider to the rightmost position."""
        self.percentage = 1.0

    def on_click(self, event: Click):
        """Move the slider to the mouse position."""
        self.percentage = event.x / self.size.width

    def on_mouse_move(self, event: MouseMove):
        """Move the slider to the mouse position."""
        if event.button != 1:
            return
        self.percentage = event.x / self.size.width
