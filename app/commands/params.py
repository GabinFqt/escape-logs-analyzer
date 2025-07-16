"""Params command implementation."""

from rich.table import Table

from app.filters import apply_filters
from app.models import LogsData
from app.utils import console, extract_request_parameters, parse_filters


def show_params(logs_data: LogsData, file_index: dict[int, str], index_file: dict[str, int], arg: str) -> None:
    """Show request parameters for a specific file.

    Usage: params <number/filename> [filters]
    Filters can be specified as key=value pairs, e.g.:
    params 1 method=GET status_code=200
    """
    if not arg:
        console.print('[red]Please specify a file name or number[/red]')
        return

    # Split the argument to separate file identifier from filters
    parts = arg.split()
    file_id = parts[0]
    filter_arg = ' '.join(parts[1:]) if len(parts) > 1 else ''
    filters = parse_filters(filter_arg)

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

    # Create table for parameters
    table = Table(title=f'Request Parameters - File #{file_num}', show_header=True, header_style='bold magenta')
    table.add_column('Parameter', style='cyan')
    table.add_column('Value', style='green')

    # Extract all parameters
    parameters = extract_request_parameters(data)

    # Add parameters to table
    for key, value in parameters:
        table.add_row(key, value)

    console.print(table)
