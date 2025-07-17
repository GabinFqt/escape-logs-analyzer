"""List command implementation."""

from rich.panel import Panel
from rich.table import Table

from app.filters import apply_filters
from app.models import Filters, LogsData
from app.utils import bytes_to_kb, console


def list_requests(logs_data: LogsData, arg: str) -> None:
    """List all requests with their details.

    Usage: list [filters]
    Filters can be specified as key=value pairs, e.g.:
    list method=GET status_code=200
    """
    filters = Filters.from_arg(arg)

    filtered_logs_data = apply_filters(filters, logs_data)

    table = Table(title='Request Details', show_header=True, header_style='bold magenta')
    table.add_column('Number', style='cyan', justify='right')
    table.add_column('Endpoint', style='green')
    table.add_column('Method', style='blue', justify='center')
    table.add_column('Status Code', justify='center')
    table.add_column('Coverage', style='cyan', justify='center')
    table.add_column('Content Type', style='yellow')
    table.add_column('Response Size', justify='right')
    table.add_column('Requester', style='magenta')

    filtered_count = 0
    for exchange in filtered_logs_data.get_all_exchanges():
        # Get response size in KB
        response_size = len(str(exchange.responseBody))
        response_size_kb = bytes_to_kb(response_size)

        table.add_row(
            str(exchange.exchangeId),
            exchange.path,
            exchange.method,
            str(exchange.inferredStatusCode),
            exchange.coverage,
            exchange.content_type,
            response_size_kb,
            exchange.requester,
        )

    console.print(table)
    if filters.at_least_one_filter():
        console.print(
            Panel(
                f'[green]Showing {filtered_count} of {logs_data.count_exchanges()} requests[/green]',
                title='Filtered Results',
            ),
        )
