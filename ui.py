# DailyDriver/ui.py
from abc import ABC, abstractmethod

class UI(ABC):
    """Abstract interface for user interaction."""

    @abstractmethod
    def clear(self):
        ...

    @abstractmethod
    def print_line(self, text: str = ""):
        ...

    @abstractmethod
    def prompt(self, text: str) -> str:
        ...

    @abstractmethod
    def confirm(self, message: str, default_yes: bool = True) -> bool:
        ...

    @abstractmethod
    def choose_from_list(self, items: list[str], prompt: str = "") -> int:
        ...

    def show_header(self, data: dict):
        """Render the daily header. Default implementation prints it."""
        from display import print_header
        print_header(data)


class TerminalUI(UI):
    """Plain terminal UI using print/input."""

    def clear(self):
        import os
        os.system('clear')

    def print_line(self, text: str = ""):
        print(text)

    def prompt(self, text: str) -> str:
        return input(text).strip()

    def confirm(self, message: str, default_yes: bool = True) -> bool:
        print(message)
        answer = input("> ").strip().lower()
        if default_yes:
            return answer == '' or answer == 'y'
        else:
            return answer == 'y'

    def choose_from_list(self, items, prompt_text="Select:"):
        for i, item in enumerate(items, 1):
            self.print_line(f"  [{i}] {item}")
        choice = self.prompt(prompt_text + " ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
        except ValueError:
            pass
        return -1


# Global instance – can be replaced at startup
current_ui: UI = TerminalUI()
