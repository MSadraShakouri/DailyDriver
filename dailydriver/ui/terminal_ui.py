# DailyDriver/ui.py
import os
from abc import ABC, abstractmethod


class UI(ABC):
    """Abstract interface for user interaction."""

    @abstractmethod
    def clear(self): ...

    @abstractmethod
    def print_line(self, text: str = ""): ...

    @abstractmethod
    def prompt(self, text: str) -> str: ...

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

    def prompt(self, text: str) -> str:
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


# Global instance – can be replaced at startup
current_ui: UI = TerminalUI()
