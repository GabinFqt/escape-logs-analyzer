"""Base LogShell class with core functionality."""

import cmd

from rich.panel import Panel

from app.models import LogsData
from app.utils import console

from .count import count_exchanges
from .info import show_info
from .list import list_requests
from .summary import show_summary


class LogShell(cmd.Cmd):
    """Interactive shell for log analysis."""

    intro = ''  # Empty intro, we'll display help manually
    prompt = '(log-analyzer) '

    # Constants
    MAX_ENDPOINT_DISPLAY_LENGTH = 50
    TRUNCATED_ENDPOINT_LENGTH = 47

    def __init__(self, logs_data: LogsData):
        console.print('[bold cyan]Welcome to the Escape Scan Debugger CLI![/bold cyan]')
        super().__init__()
        self.logs_data = logs_data

    def preloop(self) -> None:
        """Called once before the command loop starts."""
        self.do_help('')

    def do_count(self, arg: str) -> None:
        """Count the number of JSON files in the logs."""
        count_exchanges(self.logs_data, arg)

    def do_list(self, arg: str) -> None:
        """List all requests with their details."""
        list_requests(self.logs_data, arg)

    def do_summary(self, arg: str) -> None:
        """Show a summary of all endpoints grouped by name."""
        show_summary(self.logs_data, arg, self.MAX_ENDPOINT_DISPLAY_LENGTH, self.TRUNCATED_ENDPOINT_LENGTH)

    def do_info(self, arg: str) -> None:
        """Show information about specific JSON files."""
        show_info(self.logs_data, arg)

    def do_quit(self, _: str) -> bool:
        """Exit the shell."""
        console.print('[yellow]Goodbye![/yellow]')
        return True

    def do_q(self, arg: str) -> bool:
        """Alias for quit command."""
        return self.do_quit(arg)

    def do_help(self, _: str) -> None:
        """Show help for available commands."""
        help_text = """
        Available commands:
        - count [filters]: Count the number of JSON files in the logs
        - list [filters]: List all requests with their details
        - summary [full] [filters]: Show a summary of all endpoints grouped by name
        - info <number/filename> [filters] [--no-body]: Show information about a specific file
          You can also display multiple files: info 1 2 3 4
          Use --no-body to hide request and response bodies
        - params <number/filename> [filters]: Show request parameters for a specific file
        - help: Show this help message
        - quit or q: Exit the shell

        Filters can be specified as key=value pairs, e.g.:
        - method=GET
        - status_code=200
        - content_type=application/json
        - requester=oracle
        - size=100-1000
        - url=api/users
        - operation=login
        - coverage=covered
        - endpoint=/users

        You can invert any filter by adding a ! prefix, e.g.:
        - method=!GET (all methods except GET)
        - status_code=!200 (all status codes except 200)
        - content_type=!application/json (all content types except application/json)
        """
        console.print(Panel(help_text, title='Help'))

    def do_EOF(self, _: str) -> bool:
        """Handle EOF (Ctrl+D) by exiting."""
        console.print('[yellow]Goodbye![/yellow]')
        return True

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        console.print(f'[red]Unknown command: {line}[/red]')
        console.print("[yellow]Type 'help' for available commands[/yellow]")
