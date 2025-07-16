"""Info command implementation."""

from rich.markdown import Markdown
from rich.panel import Panel

from app.filters import apply_filters
from app.models import Filters, LogsData
from app.utils import console, format_json_content, get_status_description, parse_filters


def show_info(logs_data: LogsData, file_index: dict[int, str], index_file: dict[str, int], arg: str) -> None:
    """Show information about specific JSON files.

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

    # Parse file IDs and filter arguments
    file_ids, filter_arg = _parse_file_ids_and_filters(parts)
    if not file_ids:
        return

    filters = parse_filters(filter_arg)

    # Process each file ID
    for file_id in file_ids:
        _display_file_info(logs_data, file_index, index_file, file_id, filters, show_bodies)


def _parse_file_ids_and_filters(parts: list[str]) -> tuple[list[str], str]:
    """Parse file IDs and filter arguments from command parts."""
    file_ids = []
    filter_arg = ''

    # Check if the first part is a number (potential file ID)
    try:
        int(parts[0])
        # If it's a number, collect all consecutive numbers
        i = 0
        while i < len(parts) and parts[i].isdigit():
            file_ids.append(parts[i])
            i += 1
        # The rest is filter arguments
        filter_arg = ' '.join(parts[i:])
    except (ValueError, IndexError):
        # If not a number, treat as a single filename
        if parts:
            file_ids = [parts[0]]
            filter_arg = ' '.join(parts[1:])
        else:
            console.print('[red]Please specify a file name or number[/red]')
            return [], ''

    return file_ids, filter_arg


def _display_file_info(
    logs_data: LogsData,
    file_index: dict[int, str],
    index_file: dict[str, int],
    file_id: str,
    filters: Filters,
    show_bodies: bool,
) -> None:
    """Display information for a specific file."""
    # Try to parse as number first
    try:
        num = int(file_id)
        if num in file_index:
            filename = file_index[num]
        else:
            console.print(f"[red]File number '{num}' not found[/red]")
            return
    except ValueError:
        # If not a number, try as filename
        filename = file_id
        if filename not in logs_data.get_all_filenames():
            console.print(f"[red]File '{filename}' not found[/red]")
            return

    data = logs_data.get_exchange_data(filename)
    if data is None:
        console.print(f"[red]File '{filename}' not found or data is missing[/red]")
        return

    # Apply filters
    if not apply_filters(data, filters):
        console.print(f"[red]File '{filename}' does not match the specified filters[/red]")
        return

    file_num = index_file[filename]

    # Display file info as a markdown title
    markdown_title = f'# {filename} (File #{file_num})'
    console.print(Markdown(markdown_title))

    # Display request information
    request_info_list = [
        f'[cyan]URL:[/cyan] {data.url}',
        f'[cyan]Method:[/cyan] {data.method}',
        f'[cyan]Requester:[/cyan] {data.requester}',
    ]

    # Extract URL parameters if present
    if '?' in data.url:
        base_url, query_string = data.url.split('?', 1)
        request_info_list.append('\n[bold cyan]URL Parameters:[/bold cyan]')
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                request_info_list.append(f'  [yellow]{key}:[/yellow] {value}')

    if data.requestHeaders:
        request_info_list.append('\n[bold cyan]Request Headers:[/bold cyan]')
        for header in data.requestHeaders:
            if header.values:
                request_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

    console.print(Panel('\n'.join(request_info_list), title='Request Details', border_style='green'))

    # Display request body with syntax highlighting if it's JSON
    if data.requestBody and show_bodies:
        format_json_content(data.requestBody, 'Request Body', 'green')

    # Display response information with file size
    file_size_bytes = len(str(data.responseBody))
    file_size_kb = file_size_bytes / 1024
    status_description = get_status_description(str(data.responseStatusCode))

    response_info_list = [
        f'[cyan]Status Code:[/cyan] {data.responseStatusCode} ({status_description})',
        f'[cyan]Duration:[/cyan] {data.duration:.3f} s',
        f'[blue]File Size: {file_size_kb:.2f} KB[/blue]',
    ]

    if data.responseHeaders:
        response_info_list.append('\n[bold cyan]Response Headers:[/bold cyan]')
        for header in data.responseHeaders:
            if header.values:
                response_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

    console.print(Panel('\n'.join(response_info_list), title='Response Details', border_style='blue'))

    # Display response body with syntax highlighting if it's JSON
    if data.responseBody and show_bodies:
        format_json_content(data.responseBody, 'Response Body', 'blue')

    # Add a small space between files
    console.print('\n')
