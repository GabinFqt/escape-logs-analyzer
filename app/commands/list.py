"""List command implementation."""

from rich.panel import Panel
from rich.table import Table

from app.filters import apply_filters
from app.models import LogsData
from app.utils import (
    bytes_to_kb,
    clean_content_type,
    console,
    parse_filters,
)


class ListCommand:
    """List command implementation."""

    @staticmethod
    def execute(logs_data: LogsData, file_index: dict[int, str], arg: str) -> None:
        """List all requests with their details.

        Usage: list [filters]
        Filters can be specified as key=value pairs, e.g.:
        list method=GET status_code=200
        """
        filters = parse_filters(arg)

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
        for num, filename in file_index.items():
            data = logs_data.get_exchange_data(filename)
            if data is None:
                continue

            # Apply filters
            if not apply_filters(data, filters):
                continue

            filtered_count += 1

            # Extract endpoint from URL
            endpoint = data.name or 'unknown'

            # Get method
            method = data.method

            # Get status code
            status_code = data.inferredStatusCode

            # Get content type from response headers
            content_type = 'unknown'
            for header in data.responseHeaders:
                if header.name.lower() == 'content-type' and header.values:
                    content_type = clean_content_type(header.values[0])
                    break

            # Get response size in KB
            response_size = len(str(data.responseBody))
            response_size_kb = bytes_to_kb(response_size)

            # Get requester
            requester = data.requester

            # Get coverage
            coverage = data.coverage

            table.add_row(
                str(num),
                endpoint,
                method,
                str(status_code),
                coverage,
                content_type,
                response_size_kb,
                requester,
            )

        console.print(table)
        if filters.to_dict():
            console.print(
                Panel(
                    f'[green]Showing {filtered_count} of {logs_data.count_files()} requests[/green]',
                    title='Filtered Results',
                ),
            )
