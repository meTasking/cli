from typing import Any, Callable

from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text


class EditableText(Static, can_focus=True):
    """A widget that displays a static text and allows to edit it."""

    # Without min-width and min-height the user can't click on the widget
    DEFAULT_CSS = """
    EditableText {
        min-width: 2;
        min-height: 1;
    }
    """

    text: reactive[str | None] = reactive(None)
    saved_text: reactive[str | None] = reactive(None)
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
        super().__init__(self._resolve_text(text), **kwargs)
        self.update_text(text)

    def update_text(self, text: str | None) -> None:
        if text == self.saved_text:
            return

        self.text = text
        self.saved_text = text
        self.cursor = len(self.text or "")

    def _resolve_text(self, text: str | None) -> str:
        if text is None:
            if self.has_focus:
                return ""
            else:
                return self.fallback_text
        return text

    def _add_cursor(self, text: Text) -> Text:
        if self.has_focus:
            return text[:self.cursor] + Text("|") + text[self.cursor:]
        return text

    def _update_text(self) -> None:
        saved_text = self.saved_text or ""
        final_text = self._resolve_text(self.text)
        differs = self.saved_text != self.text

        if differs and self.text is not None:
            enriched_text = Text()
            for i, c in enumerate(final_text):
                t = Text(c)
                if i >= len(saved_text) or c != saved_text[i]:
                    t.stylize("bold")
                enriched_text.append(t)
        else:
            enriched_text = Text(final_text)

        if differs:
            enriched_text.append(Text("*", style="red"))

        self.update(self._add_cursor(enriched_text))

    def watch_text(self, new_value: str | None) -> None:
        self.call_after_refresh(self._update_text)

    def watch_saved_text(self, new_value: str | None) -> None:
        self.call_after_refresh(self._update_text)

    def watch_cursor(self, new_value: int) -> None:
        self.call_after_refresh(self._update_text)

    def on_focus(self, event) -> None:
        self.call_after_refresh(self._update_text)

    def on_blur(self, event) -> None:
        self.call_after_refresh(self._update_text)

    def key_enter(self) -> None:
        if self.save_callback is not None:
            self.save_callback(self.text)
        self.saved_text = self.text
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

    def key_ctrl_left(self) -> None:
        if self.text is None:
            return

        if self.cursor == 0:
            return

        text = self.text
        if text[self.cursor - 1] == " ":
            self.cursor -= 1
            return

        for i in range(self.cursor - 1, -1, -1):
            if text[i] == " ":
                self.cursor = i + 1
                return

        self.cursor = 0

    def key_ctrl_right(self) -> None:
        if self.text is None:
            return

        if self.cursor >= len(self.text):
            return

        text = self.text
        if text[self.cursor] == " ":
            self.cursor += 1
            return

        for i in range(self.cursor, len(text)):
            if text[i] == " ":
                self.cursor = i
                return

        self.cursor = len(text)

    def on_key(self, event: Key) -> None:
        if event.character is None or not event.is_printable:
            return

        text = self.text
        if text is None:
            text = ""

        text = text[:self.cursor] + event.character + text[self.cursor:]
        self.cursor += 1
        self.text = text
