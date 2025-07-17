"""Summary command implementation."""

from rich.panel import Panel
from rich.table import Table

from app.filters import apply_filters
from app.models import EndpointsInfoData, Filters, LogsData
from app.utils import console


def show_summary(
    logs_data: LogsData,
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

    filters = Filters.from_arg(filter_arg)

    filtered_logs_data = apply_filters(filters, logs_data)
    endpoints_info_data = EndpointsInfoData.from_logs_data(filtered_logs_data)

    table = Table(title='Named Groups Summary', show_header=True, header_style='bold magenta')
    table.add_column('ID', style='bold white', justify='center')
    table.add_column('Name', style='cyan')
    table.add_column('Endpoints', style='green')
    table.add_column('Methods', justify='center', style='blue')
    table.add_column('Status Codes', justify='center')
    table.add_column('Coverage', justify='center')
    table.add_column('Inferred Status Codes', justify='center')
    table.add_column('Request Count', justify='right', style='yellow')

    for endpoint_info in endpoints_info_data.get_all_endpoints():
        # Format endpoints for display
        endpoints_display = ', '.join(sorted(endpoint_info.path))
        if not show_full_urls and len(endpoints_display) > max_endpoint_display_length:
            endpoints_display = endpoints_display[:truncated_endpoint_length] + '...'

        table.add_row(
            endpoint_info.path,
            endpoint_info.method,
            endpoints_display,
            ', '.join(sorted(endpoint_info.methods)),
            ', '.join(sorted(str(code) for code in endpoint_info.status_codes)),
            ', '.join(sorted(str(code) for code in endpoint_info.inferred_status_codes)),
            str(endpoint_info.count_exchanges),
        )

    console.print(table)
    if not show_full_urls:
        console.print("[yellow]Tip: Use 'summary full' to see complete endpoint URLs[/yellow]")

    if filters.at_least_one_filter():
        unfiltered_endpoints_info_data = EndpointsInfoData.from_logs_data(logs_data)
        console.print(
            Panel(
                f'[green]Showing summary for {len(endpoints_info_data)} of {len(unfiltered_endpoints_info_data)} named[/green]',
                title='Filtered Results',
            ),
        )
