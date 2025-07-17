"""Count command implementation."""

from rich.panel import Panel

from app.filters import apply_filters
from app.models import Filters, LogsData
from app.utils import console


def count_exchanges(logs_data: LogsData, arg: str) -> None:
    """Count the number of exchanges in the logs.

    Usage: count [filters]
    Filters can be specified as key=value pairs, e.g.:
    count method=GET status_code=200
    """
    filters = Filters.from_arg(arg)
    filtered_logs_data = apply_filters(filters, logs_data)

    console.print(Panel(f'[blue]Total exchanges: {logs_data.count_exchanges()}[/blue]', title='Count'))
    if filters.at_least_one_filter():
        console.print(
            Panel(f'[green]Filtered exchanges: {filtered_logs_data.count_exchanges()}[/green]', title='Filtered Count')
        )
