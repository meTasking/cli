from enum import Enum

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text


class BarCS(Enum):
    EMPTY = 0
    FULL = 1
    LEFT = 2
    RIGHT = 3

    def merge(self, other: "BarCS") -> "BarCS":
        if self == BarCS.EMPTY:
            return other
        elif self == BarCS.FULL:
            return self
        elif self == BarCS.LEFT:
            if other == BarCS.RIGHT:
                return BarCS.FULL
            elif other == BarCS.FULL:
                return other
            else:
                return self
        elif self == BarCS.RIGHT:
            if other == BarCS.LEFT:
                return BarCS.FULL
            elif other == BarCS.FULL:
                return other
            else:
                return self
        else:
            raise Exception("Unknown state")


class RangeBar:
    def __init__(
        self,
        highlighted_ranges: list[tuple[float, float]] = [],
    ) -> None:
        self.highlighted_ranges = highlighted_ranges

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        highlight_style = console.get_style("dark_cyan")
        background_style = console.get_style("grey37")

        width = options.max_width
        content: list[BarCS] = list(
            BarCS.EMPTY for _ in range(width)
        )

        for highlight_range in self.highlighted_ranges:
            start, end = highlight_range

            start *= width
            end *= width

            start = max(start, 0)
            end = min(end, width)

            underflow = start % 1
            overflow = end % 1

            start = int(start)
            if underflow >= 0.5:
                content[start] = content[start]\
                    .merge(BarCS.LEFT)
                start += 1

            end = int(end)
            if overflow >= 0.5:
                content[end + 1] = content[end + 1]\
                    .merge(BarCS.RIGHT)

            for i in range(start, end):
                content[i] = content[i].merge(BarCS.FULL)

        for i in range(len(content)):
            c_prev = content[i - 1] if i > 0 else None
            c_curr = content[i]
            c_next = content[i + 1] if i < len(content) - 1 else None

            # E -> E '━━'
            # E -> L '━╺'
            # E -> R '╸╸'
            # E -> F '╸━'
            # L -> E '╺╺'
            # L -> L '╺╺'
            # L -> R '╺╸'
            # L -> F '╺━'
            # R -> E '╸━'
            # R -> L '╸╺'
            # R -> R '╸╸'
            # R -> F '╸━'
            # F -> E '━╺'
            # F -> L '━╺'
            # F -> R '━╸'
            # F -> F '━━'

            match (c_prev, c_curr, c_next):
                case (BarCS.EMPTY, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.EMPTY, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.EMPTY, BarCS.EMPTY, None) | \
                        (BarCS.RIGHT, BarCS.EMPTY, None) | \
                        (None, BarCS.EMPTY, BarCS.EMPTY) | \
                        (None, BarCS.EMPTY, BarCS.LEFT):
                    yield Text("━", style=background_style, end="")
                case (BarCS.LEFT, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.LEFT, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.EMPTY) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.LEFT) | \
                        (BarCS.LEFT, BarCS.EMPTY, None) | \
                        (BarCS.FULL, BarCS.EMPTY, None):
                    yield Text("╺", style=background_style, end="")
                case (BarCS.EMPTY, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.EMPTY, BarCS.EMPTY, BarCS.FULL) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.RIGHT, BarCS.EMPTY, BarCS.FULL) | \
                        (None, BarCS.EMPTY, BarCS.RIGHT) | \
                        (None, BarCS.EMPTY, BarCS.FULL):
                    yield Text("╸", style=background_style, end="")
                case (BarCS.LEFT, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.LEFT, BarCS.EMPTY, BarCS.FULL) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.RIGHT) | \
                        (BarCS.FULL, BarCS.EMPTY, BarCS.FULL):
                    # This is conflict between two conversions
                    # Let's just add space - there will be more blank space
                    yield Text(" ", style=background_style, end="")
                case (_, BarCS.LEFT, _):
                    yield Text("╺", style=highlight_style, end="")
                case (_, BarCS.RIGHT, _):
                    yield Text("╸", style=highlight_style, end="")
                case (_, BarCS.FULL, _):
                    yield Text("━", style=highlight_style, end="")
                case _:
                    raise Exception("Unhandled bar state")

        # Fire actions when certain ranges are clicked (e.g. for tabs)
        # for range_name, (start, end) in self.clickable_ranges.items():
        #     output_bar.apply_meta(
        #         {"@click": f"range_clicked('{range_name}')"}, start, end
        #     )

        pass
