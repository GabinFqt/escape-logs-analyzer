"""Info command implementation."""

from rich.markdown import Markdown
from rich.panel import Panel

from app.filters import apply_filters
from app.models import Filters, LogsData
from app.utils import console, extract_request_info, extract_response_info, format_json_content, parse_filters


class InfoCommand:
    """Info command implementation."""

    @staticmethod
    def execute(logs_data: LogsData, file_index: dict[int, str], index_file: dict[str, int], arg: str) -> None:
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
        file_ids, filter_arg = InfoCommand._parse_file_ids_and_filters(parts)
        if not file_ids:
            return

        filters = parse_filters(filter_arg)

        # Process each file ID
        for file_id in file_ids:
            InfoCommand._display_file_info(logs_data, file_index, index_file, file_id, filters, show_bodies)

    @staticmethod
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

    @staticmethod
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
        request_info = extract_request_info(data)
        request_info_list = [
            f'[cyan]URL:[/cyan] {request_info.url}',
            f'[cyan]Method:[/cyan] {request_info.method}',
            f'[cyan]Requester:[/cyan] {request_info.requester}',
        ]

        if request_info.url_parameters and request_info.url_parameters.parameters:
            request_info_list.append('\n[bold cyan]URL Parameters:[/bold cyan]')
            for key, value in request_info.url_parameters.parameters.items():
                request_info_list.append(f'  [yellow]{key}:[/yellow] {value}')

        if request_info.headers:
            request_info_list.append('\n[bold cyan]Request Headers:[/bold cyan]')
            for header in request_info.headers:
                if header.values:
                    request_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

        console.print(Panel('\n'.join(request_info_list), title='Request Details', border_style='green'))

        # Display request body with syntax highlighting if it's JSON
        request_body = data.requestBody
        if request_body and show_bodies:
            format_json_content(request_body, 'Request Body', 'green')

        # Display response information with file size
        response_info = extract_response_info(data)
        file_size_bytes = len(str(data.responseBody))
        file_size_kb = file_size_bytes / 1024
        response_info_list = [
            f'[cyan]Status Code:[/cyan] {response_info.status_code} ({response_info.status_description})',
            f'[cyan]Duration:[/cyan] {response_info.duration:.3f} s',
            f'[blue]File Size: {file_size_kb:.2f} KB[/blue]',
        ]

        if response_info.headers:
            response_info_list.append('\n[bold cyan]Response Headers:[/bold cyan]')
            for header in response_info.headers:
                if header.values:
                    response_info_list.append(f'  [yellow]{header.name}:[/yellow] {header.values[0]}')

        console.print(Panel('\n'.join(response_info_list), title='Response Details', border_style='blue'))

        # Display response body with syntax highlighting if it's JSON
        response_body = data.responseBody
        if response_body and show_bodies:
            format_json_content(response_body, 'Response Body', 'blue')

        # Add a small space between files
        console.print('\n')
