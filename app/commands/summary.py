"""Summary command implementation."""

from typing import Any

from rich.panel import Panel
from rich.table import Table

from app.filters import apply_filters
from app.models import Filters, GroupIds, LogsData, RequestCounts
from app.utils import console, parse_filters


class SummaryCommand:
    """Summary command implementation."""

    @staticmethod
    def execute(
        logs_data: LogsData,
        endpoints: dict[str, Any],
        arg: str,
        max_endpoint_display_length: int,
        truncated_endpoint_length: int,
    ) -> None:
        """Show a summary of all endpoints grouped by name.

        Usage: summary [full] [filters]
        If 'full' is specified, displays the complete URLs including domain.
        Filters can be specified as key=value pairs, e.g.:
        summary full method=GET status_code=200
        """
        # Parse arguments
        parts = arg.split() if arg else []
        show_full_urls = False
        filter_arg = ''

        if parts and parts[0].lower() == 'full':
            show_full_urls = True
            filter_arg = ' '.join(parts[1:])
        else:
            filter_arg = arg

        filters = parse_filters(filter_arg)

        table = Table(title='Named Groups Summary', show_header=True, header_style='bold magenta')
        table.add_column('ID', style='bold white', justify='center')
        table.add_column('Name', style='cyan')
        table.add_column('Endpoints', style='green')
        table.add_column('Methods', justify='center', style='blue')
        table.add_column('Status Codes', justify='center')
        table.add_column('Request Count', justify='right', style='yellow')

        # Generate IDs for named groups (A, B, C, ..., Z, AA, AB, ...)
        group_ids = GroupIds.generate(endpoints)

        # Count requests per named group with filters
        request_counts_obj = SummaryCommand._count_requests_by_group(logs_data, filters)

        for name, data in sorted(endpoints.items()):
            # Skip groups with no matching requests after filtering
            if filters.to_dict() and name not in request_counts_obj.filtered_groups:
                continue

            # Format endpoints for display
            endpoints_display = ', '.join(sorted(data.endpoints))
            if not show_full_urls and len(endpoints_display) > max_endpoint_display_length:
                endpoints_display = endpoints_display[:truncated_endpoint_length] + '...'

            table.add_row(
                group_ids.group_ids[name],
                name,
                endpoints_display,
                ', '.join(sorted(data.methods)),
                ', '.join(sorted(str(code) for code in data.status_codes)),
                str(request_counts_obj.request_counts.get(name, 0)),
            )

        console.print(table)
        if not show_full_urls:
            console.print("[yellow]Tip: Use 'summary full' to see complete endpoint URLs[/yellow]")
        if filters.to_dict():
            console.print(
                Panel(
                    f'[green]Showing summary for {len(request_counts_obj.filtered_groups)} of {len(endpoints)} named groups[/green]',
                    title='Filtered Results',
                ),
            )

    @staticmethod
    def _count_requests_by_group(logs_data: LogsData, filters: Filters) -> RequestCounts:
        """Count requests per named group with filters."""
        request_counts: dict[str, int] = {}
        filtered_groups = set()

        for filename in logs_data.get_all_filenames():
            data = logs_data.get_exchange_data(filename)
            if data is None:
                continue

            if not apply_filters(data, filters):
                continue

            # Get the name field from the request body or use endpoint as fallback
            name = data.name or 'unknown'

            request_counts[name] = request_counts.get(name, 0) + 1
            filtered_groups.add(name)

        return RequestCounts(request_counts=request_counts, filtered_groups=filtered_groups)
