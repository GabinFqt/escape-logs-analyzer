"""Info command implementation."""

from rich.markdown import Markdown
from rich.panel import Panel

from app.models import ExchangeId, LogsData
from app.utils import console, format_json_content, get_status_description


def show_info(logs_data: LogsData, arg: str) -> None:
    """Show information about specific Exchange

    Usage: info <number/filename> [filters] or info <number1> <number2> <number3> ...
    Filters can be specified as key=value pairs, e.g.:
    info 1 method=GET status_code=200
    Or display multiple files:
    info 1 2 3 4

    Options:
    --no-body: Do not display request and response bodies
    """
    if not arg:
        console.print('[red]Please specify a file name or number[/red]')
        return

    # Split the argument to separate file identifiers from filters
    parts = arg.split()

    # Check for options
    show_bodies = True
    if '--no-body' in parts:
        show_bodies = False
        parts.remove('--no-body')

    # Process each file ID
    for exchange in logs_data.get_all_exchanges():
        _display_file_info(logs_data, exchange.exchangeId, show_bodies)


def _display_file_info(
    logs_data: LogsData,
    exchange_id: ExchangeId,
    show_bodies: bool,
) -> None:
    """Display information for a specific exchange."""
    exchange = logs_data.get_exchange_by_id(exchange_id)
    if exchange is None:
        console.print(f"[red]Exchange '{exchange_id}' not found or data is missing[/red]")
        return

    # Display exchange info as a markdown title
    markdown_title = f'# {exchange.exchangeId}'
    console.print(Markdown(markdown_title))

    # Display request information
    request_info_list = [
        f'[cyan]URL:[/cyan] {exchange.url}',
        f'[cyan]Method:[/cyan] {exchange.method}',
        f'[cyan]Requester:[/cyan] {exchange.requester}',
    ]

    # Extract URL parameters if present
    if '?' in exchange.url:
        base_url, query_string = exchange.url.split('?', 1)
        request_info_list.append('\n[bold cyan]URL Parameters:[/bold cyan]')
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                request_info_list.append(f'  [yellow]{key}:[/yellow] {value}')

    if exchange.requestHeaders:
        request_info_list.append('\n[bold cyan]Request Headers:[/bold cyan]')
        for header in exchange.requestHeaders:
            if header.values:
                request_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

    console.print(Panel('\n'.join(request_info_list), title='Request Details', border_style='green'))

    # Display request body with syntax highlighting if it's JSON
    if exchange.requestBody and show_bodies:
        format_json_content(exchange.requestBody, 'Request Body', 'green')

    # Display response information with file size
    file_size_bytes = len(str(exchange.responseBody))
    file_size_kb = file_size_bytes / 1024
    status_description = get_status_description(str(exchange.responseStatusCode))

    response_info_list = [
        f'[cyan]Status Code:[/cyan] {exchange.responseStatusCode} ({status_description})',
        f'[cyan]Duration:[/cyan] {exchange.duration:.3f} s',
        f'[blue]File Size: {file_size_kb:.2f} KB[/blue]',
    ]

    if exchange.responseHeaders:
        response_info_list.append('\n[bold cyan]Response Headers:[/bold cyan]')
        for header in exchange.responseHeaders:
            if header.values:
                response_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

    console.print(Panel('\n'.join(response_info_list), title='Response Details', border_style='blue'))

    # Display response body with syntax highlighting if it's JSON
    if exchange.responseBody and show_bodies:
        format_json_content(exchange.responseBody, 'Response Body', 'blue')

    # Add a small space between files
    console.print('\n')
