# DailyDriver/ui/terminal_ui.py
import os
from abc import ABC, abstractmethod


class UI(ABC):
    """Abstract interface for user interaction.

    Only *input* is abstracted. Output (headers, tables, calendars) is plain
    ``print`` and is shared by every backend. The ``prompt`` method accepts
    optional ``completions`` and ``history_key`` hints; plain backends ignore
    them while rich backends (prompt_toolkit) use them for autocompletion and
    persistent history.
    """

    @abstractmethod
    def clear(self): ...

    @abstractmethod
    def print_line(self, text: str = ""): ...

    @abstractmethod
    def prompt(self, text: str, completions: list[str] | None = None, history_key: str | None = None) -> str: ...

    @abstractmethod
    def confirm(self, message: str, default_yes: bool = True) -> bool:
        """Show a message and ask for confirmation. Return True to proceed."""
        ...

    @abstractmethod
    def confirm_time(self, start_str: str, dur_str: str = "") -> bool:
        """Ask user to confirm a time/duration. Return True to proceed."""
        ...

    @abstractmethod
    def choose_from_list(self, items: list[str], prompt: str = "") -> int: ...

    def select_categories(
        self,
        matches: list[tuple[str, float]],
        all_paths: list[str],
        show_great_only: bool = False,
    ) -> list[str] | None:
        """Interactively select one or more category paths.

        Returns the chosen paths (possibly empty for "Great Event only"), or
        ``None`` to signal that the caller should fall back to its own text
        flow. The default returns ``None`` so plain backends keep their existing
        numbered-list behavior; rich backends override this with an
        autocompleting picker.
        """
        return None

    def show_header(self, data: dict):
        """Render the daily header. Default implementation prints it."""
        from dailydriver.display.header_renderer import print_header

        print_header(data)


class TerminalUI(UI):
    """Plain terminal UI using print/input."""

    def clear(self):
        os.system("clear")

    def print_line(self, text: str = ""):
        print(text)

    def prompt(self, text: str, completions: list[str] | None = None, history_key: str | None = None) -> str:
        # completions/history_key are ignored by the plain backend.
        return input(text).strip()

    def confirm(self, message: str, default_yes: bool = True) -> bool:
        self.print_line()
        self.print_line(message)
        if default_yes:
            self.print_line("(Enter=yes, n=cancel)")
        else:
            self.print_line("(y=yes, Enter=cancel)")
        answer = self.prompt("> ").strip().lower()
        if default_yes:
            return answer == "" or answer == "y"
        else:
            return answer == "y"

    def confirm_time(self, start_str: str, dur_str: str = "") -> bool:
        self.print_line()
        self.print_line(f"Time:   {start_str}")
        if dur_str:
            self.print_line(f"Duration: {dur_str}")
        self.print_line("(Enter=yes, n=cancel)")
        answer = self.prompt("> ").strip().lower()
        return answer == "" or answer == "y"

    def choose_from_list(self, items, prompt="Select:"):
        for i, item in enumerate(items, 1):
            self.print_line(f"  [{i}] {item}")
        choice = self.prompt(prompt + " ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
        except ValueError:
            pass
        return -1


def select_ui() -> UI:
    """Choose the best available input backend.

    Prefers the prompt_toolkit backend for interactive terminals, and falls
    back to the plain :class:`TerminalUI` when prompt_toolkit is unavailable or
    stdin/stdout is not an interactive TTY (piped input, redirects, dumb
    terminals, most test contexts). The fallback behaves exactly as the app did
    before prompt_toolkit was introduced, so nothing breaks if it cannot run.
    """
    import sys

    try:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return TerminalUI()
    except Exception:
        return TerminalUI()

    try:
        from dailydriver.ui.ptk_ui import PromptToolkitUI

        return PromptToolkitUI()
    except Exception:
        return TerminalUI()


# Global instance – resolved at import time, can be replaced at startup.
current_ui: UI = select_ui()
