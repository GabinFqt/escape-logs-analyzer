import cmd
import json
import zipfile
from pathlib import Path
from typing import Any

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from app.filters import apply_filters
from app.models import LogsData
from app.utils import (
    bytes_to_kb,
    clean_content_type,
    console,
    extract_endpoints,
    extract_path_from_url,
    extract_request_info,
    extract_request_parameters,
    extract_response_info,
    format_json_content,
    parse_filters,
)


def process_zip(zip_path: Path) -> LogsData:
    """Process zip file and return logs data as LogsData model."""
    logs_data = {}
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.json'):
                with zip_ref.open(file_name) as f:
                    logs_data[file_name] = json.load(f)
    console.print(
        Panel(f'[green]Successfully decompressed {len(logs_data)} JSON files[/green]', title='Zip Processing'),
    )
    return LogsData.from_dict(logs_data)


class LogShell(cmd.Cmd):
    """Interactive shell for log analysis."""

    intro = ''  # Empty intro, we'll display help manually
    prompt = '(log-analyzer) '

    # Constants
    MAX_ENDPOINT_DISPLAY_LENGTH = 50
    TRUNCATED_ENDPOINT_LENGTH = 47

    def __init__(self, logs_data: LogsData):
        console.print('[bold cyan]Welcome to the Escape Scan Debugger CLI![/bold cyan]')
        super().__init__()
        self.logs_data = logs_data
        self.file_index = {i + 1: filename for i, filename in enumerate(sorted(logs_data.get_all_filenames()))}
        self.index_file = {filename: i + 1 for i, filename in enumerate(sorted(logs_data.get_all_filenames()))}
        # For endpoints extraction, pass a dict of filename: dict (not model)
        raw_dict = {}
        for fn in logs_data.get_all_filenames():
            data = logs_data.get_exchange_data(fn)
            if data is not None:
                raw_dict[fn] = data.dict()
        self.endpoints = extract_endpoints(raw_dict)

    def preloop(self) -> None:
        """Called once before the command loop starts."""
        self.do_help('')

    def do_count(self, arg: str) -> None:
        """Count the number of JSON files in the logs.

        Usage: count [filters]
        Filters can be specified as key=value pairs, e.g.:
        count method=GET status_code=200
        """
        filters = parse_filters(arg)
        filtered_count = 0
        for filename in self.logs_data.get_all_filenames():
            data = self.logs_data.get_exchange_data(filename)
            if data is not None and apply_filters(data.dict(), filters):
                filtered_count += 1

        console.print(Panel(f'[blue]Total JSON files: {self.logs_data.count_files()}[/blue]', title='Count'))
        if filters:
            console.print(Panel(f'[green]Filtered JSON files: {filtered_count}[/green]', title='Filtered Count'))

    def do_list(self, arg: str) -> None:
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
        for num, filename in self.file_index.items():
            data = self.logs_data.get_exchange_data(filename)
            if data is None:
                continue

            # Apply filters (convert to dict for compatibility)
            if not apply_filters(data.dict(), filters):
                continue

            filtered_count += 1

            # Extract endpoint from URL
            endpoint = extract_path_from_url(data.url)

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
        if filters:
            console.print(
                Panel(
                    f'[green]Showing {filtered_count} of {self.logs_data.count_files()} requests[/green]',
                    title='Filtered Results',
                ),
            )

    def do_summary(self, arg: str) -> None:
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
        group_ids = self._generate_group_ids()

        # Count requests per named group with filters
        request_counts, filtered_groups = self._count_requests_by_group(filters)

        for name, data in sorted(self.endpoints.items()):
            # Skip groups with no matching requests after filtering
            if filters and name not in filtered_groups:
                continue

            # Format endpoints for display
            endpoints_display = ', '.join(sorted(data['endpoints']))
            if not show_full_urls and len(endpoints_display) > self.MAX_ENDPOINT_DISPLAY_LENGTH:
                endpoints_display = endpoints_display[: self.TRUNCATED_ENDPOINT_LENGTH] + '...'

            table.add_row(
                group_ids[name],
                name,
                endpoints_display,
                ', '.join(sorted(data['methods'])),
                ', '.join(sorted(str(code) for code in data['status_codes'])),
                str(request_counts.get(name, 0)),
            )

        console.print(table)
        if not show_full_urls:
            console.print("[yellow]Tip: Use 'summary full' to see complete endpoint URLs[/yellow]")
        if filters:
            console.print(
                Panel(
                    f'[green]Showing summary for {len(filtered_groups)} of {len(self.endpoints)} named groups[/green]',
                    title='Filtered Results',
                ),
            )

    def _generate_group_ids(self) -> dict[str, str]:
        """Generate IDs for named groups (A, B, C, ..., Z, AA, AB, ...)."""
        group_ids = {}
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        for current_id, name in enumerate(sorted(self.endpoints.keys())):
            # Generate ID (A, B, C, ..., Z, AA, AB, ...)
            id_str = ''
            temp_id = current_id
            while temp_id >= 0:
                id_str = alphabet[temp_id % 26] + id_str
                temp_id = temp_id // 26 - 1
            group_ids[name] = id_str

        return group_ids

    def _count_requests_by_group(self, filters: dict[str, Any]) -> tuple[dict[str, int], set[str]]:
        """Count requests per named group with filters."""
        request_counts: dict[str, int] = {}
        filtered_groups = set()

        for filename in self.logs_data.get_all_filenames():
            data = self.logs_data.get_exchange_data(filename)
            if data is None:
                continue

            if not apply_filters(data.dict(), filters):
                continue

            # Get the name field from the request body or use endpoint as fallback
            name = 'unknown'
            request_body = data.requestBody
            if request_body:
                try:
                    body_json = json.loads(request_body)
                    name = body_json.get('name', extract_path_from_url(data.url))
                except json.JSONDecodeError:
                    name = extract_path_from_url(data.url)
            else:
                name = extract_path_from_url(data.url)

            request_counts[name] = request_counts.get(name, 0) + 1
            filtered_groups.add(name)

        return request_counts, filtered_groups

    def do_info(self, arg: str) -> None:
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
        file_ids, filter_arg = self._parse_file_ids_and_filters(parts)
        if not file_ids:
            return

        filters = parse_filters(filter_arg)

        # Process each file ID
        for file_id in file_ids:
            self._display_file_info(file_id, filters, show_bodies)

    def _parse_file_ids_and_filters(self, parts: list[str]) -> tuple[list[str], str]:
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

    def _display_file_info(self, file_id: str, filters: dict[str, Any], show_bodies: bool) -> None:
        """Display information for a specific file."""
        # Try to parse as number first
        try:
            num = int(file_id)
            if num in self.file_index:
                filename = self.file_index[num]
            else:
                console.print(f"[red]File number '{num}' not found[/red]")
                return
        except ValueError:
            # If not a number, try as filename
            filename = file_id
            if filename not in self.logs_data.get_all_filenames():
                console.print(f"[red]File '{filename}' not found[/red]")
                return

        data = self.logs_data.get_exchange_data(filename)
        if data is None:
            console.print(f"[red]File '{filename}' not found or data is missing[/red]")
            return

        # Apply filters
        if not apply_filters(data.dict(), filters):
            console.print(f"[red]File '{filename}' does not match the specified filters[/red]")
            return

        file_num = self.index_file[filename]

        # Display file info as a markdown title
        markdown_title = f'# {filename} (File #{file_num})'
        console.print(Markdown(markdown_title))

        # Display request information
        request_info = extract_request_info(data.dict())
        console.print(Panel('\n'.join(request_info), title='Request Details', border_style='green'))

        # Display request body with syntax highlighting if it's JSON
        request_body = data.requestBody
        if request_body and show_bodies:
            format_json_content(request_body, 'Request Body', 'green')

        # Display response information with file size
        response_info = extract_response_info(data.dict())
        file_size_bytes = len(str(data.responseBody))
        file_size_kb = file_size_bytes / 1024
        response_info.append(f'[blue]File Size: {file_size_kb:.2f} KB[/blue]')
        console.print(Panel('\n'.join(response_info), title='Response Details', border_style='blue'))

        # Display response body with syntax highlighting if it's JSON
        response_body = data.responseBody
        if response_body and show_bodies:
            format_json_content(response_body, 'Response Body', 'blue')

        # Add a small space between files
        console.print('\n')

    def do_params(self, arg: str) -> None:
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
            if num in self.file_index:
                filename = self.file_index[num]
            else:
                console.print(f"[red]File number '{num}' not found[/red]")
                return
        except ValueError:
            # If not a number, try as filename
            filename = file_id
            if filename not in self.logs_data.get_all_filenames():
                console.print(f"[red]File '{filename}' not found[/red]")
                return

        data = self.logs_data.get_exchange_data(filename)
        if data is None:
            console.print(f"[red]File '{filename}' not found or data is missing[/red]")
            return

        # Apply filters
        if not apply_filters(data.dict(), filters):
            console.print(f"[red]File '{filename}' does not match the specified filters[/red]")
            return

        file_num = self.index_file[filename]

        # Create table for parameters
        table = Table(title=f'Request Parameters - File #{file_num}', show_header=True, header_style='bold magenta')
        table.add_column('Parameter', style='cyan')
        table.add_column('Value', style='green')

        # Extract all parameters
        parameters = extract_request_parameters(data.dict())

        # Add parameters to table
        for key, value in parameters:
            table.add_row(key, value)

        console.print(table)

    def do_quit(self, _: str) -> bool:
        """Exit the shell."""
        console.print('[yellow]Goodbye![/yellow]')
        return True

    def do_q(self, arg: str) -> bool:
        """Alias for quit command."""
        return self.do_quit(arg)

    def do_help(self, _: str) -> None:
        """Show help for available commands."""
        help_text = """
        Available commands:
        - list [filters]: List all requests with their details
        - info <number/filename> [filters] [--no-body]: Show information about a specific file
          You can also display multiple files: info 1 2 3 4
          Use --no-body to hide request and response bodies
        - help: Show this help message
        - quit or q: Exit the shell

        Filters can be specified as key=value pairs, e.g.:
        - method=GET
        - status_code=200
        - content_type=application/json
        - requester=oracle
        - size=100-1000
        - url=api/users
        - operation=login
        - coverage=covered
        - endpoint=/users

        You can invert any filter by adding a ! prefix, e.g.:
        - method=!GET (all methods except GET)
        - status_code=!200 (all status codes except 200)
        - content_type=!application/json (all content types except application/json)
        """
        console.print(Panel(help_text, title='Help'))

    def do_EOF(self, _: str) -> bool:
        """Handle EOF (Ctrl+D) by exiting."""
        console.print('[yellow]Goodbye![/yellow]')
        return True

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        console.print(f'[red]Unknown command: {line}[/red]')
        console.print("[yellow]Type 'help' for available commands[/yellow]")


def start_shell(logs_data: LogsData) -> None:
    """Start the interactive shell with the processed logs data."""
    LogShell(logs_data).cmdloop()
