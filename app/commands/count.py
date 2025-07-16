"""Count command implementation."""

from rich.panel import Panel

from app.filters import apply_filters
from app.models import LogsData
from app.utils import console, parse_filters


class CountCommand:
    """Count command implementation."""

    @staticmethod
    def execute(logs_data: LogsData, arg: str) -> None:
        """Count the number of JSON files in the logs.

        Usage: count [filters]
        Filters can be specified as key=value pairs, e.g.:
        count method=GET status_code=200
        """
        filters = parse_filters(arg)
        filtered_count = 0
        for filename in logs_data.get_all_filenames():
            data = logs_data.get_exchange_data(filename)
            if data is not None and apply_filters(data, filters):
                filtered_count += 1

        console.print(Panel(f'[blue]Total JSON files: {logs_data.count_files()}[/blue]', title='Count'))
        if filters.to_dict():
            console.print(Panel(f'[green]Filtered JSON files: {filtered_count}[/green]', title='Filtered Count'))
