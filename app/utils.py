import json
import shlex
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


HTTP_STATUS_DESCRIPTIONS = {
    '100': 'Continue',
    '101': 'Switching Protocols',
    '102': 'Processing',
    '200': 'OK',
    '201': 'Created',
    '202': 'Accepted',
    '203': 'Non-Authoritative Information',
    '204': 'No Content',
    '205': 'Reset Content',
    '206': 'Partial Content',
    '207': 'Multi-Status',
    '208': 'Already Reported',
    '226': 'IM Used',
    '300': 'Multiple Choices',
    '301': 'Moved Permanently',
    '302': 'Found',
    '303': 'See Other',
    '304': 'Not Modified',
    '305': 'Use Proxy',
    '307': 'Temporary Redirect',
    '308': 'Permanent Redirect',
    '400': 'Bad Request',
    '401': 'Unauthorized',
    '402': 'Payment Required',
    '403': 'Forbidden',
    '404': 'Not Found',
    '405': 'Method Not Allowed',
    '406': 'Not Acceptable',
    '407': 'Proxy Authentication Required',
    '408': 'Request Timeout',
    '409': 'Conflict',
    '410': 'Gone',
    '411': 'Length Required',
    '412': 'Precondition Failed',
    '413': 'Payload Too Large',
    '414': 'URI Too Long',
    '415': 'Unsupported Media Type',
    '416': 'Range Not Satisfiable',
    '417': 'Expectation Failed',
    '418': "I'm a Teapot",
    '421': 'Misdirected Request',
    '422': 'Unprocessable Entity',
    '423': 'Locked',
    '424': 'Failed Dependency',
    '425': 'Too Early',
    '426': 'Upgrade Required',
    '428': 'Precondition Required',
    '429': 'Too Many Requests',
    '431': 'Request Header Fields Too Large',
    '451': 'Unavailable For Legal Reasons',
    '500': 'Internal Server Error',
    '501': 'Not Implemented',
    '502': 'Bad Gateway',
    '503': 'Service Unavailable',
    '504': 'Gateway Timeout',
    '505': 'HTTP Version Not Supported',
    '506': 'Variant Also Negotiates',
    '507': 'Insufficient Storage',
    '508': 'Loop Detected',
    '510': 'Not Extended',
    '511': 'Network Authentication Required',
    '520': 'Web Server Returned an Unknown Error',
    '521': 'Web Server Is Down',
    '522': 'Connection Timed Out',
    '524': 'A Timeout Occurred',
    '599': 'Network Connect Timeout Error',
}


def extract_path_from_url(url: str) -> str:
    """Extract the path from a URL, removing the domain and query parameters."""
    try:
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        return parsed_url.path
    except Exception:
        return url


def get_size_range(sizes: list[int]) -> str:
    """Get a human-readable size range."""
    if not sizes:
        return 'N/A'

    min_size = min(sizes)
    max_size = max(sizes)

    if min_size == max_size:
        return f'{min_size} bytes'

    return f'{min_size}-{max_size} bytes'


def clean_content_type(content_type: str) -> str:
    """Clean content type by removing charset for application/json."""
    if content_type.startswith('application/json'):
        return 'application/json'
    return content_type


def bytes_to_kb(bytes_size: int) -> str:
    """Convert bytes to KB with 2 decimal places."""
    return f'{bytes_size / 1024:.2f} KB'


def get_status_description(status_code: str) -> str:
    """Get a human-readable description for an HTTP status code."""
    return HTTP_STATUS_DESCRIPTIONS.get(status_code, 'Unknown')


def parse_filters(arg: str) -> dict[str, str]:
    """Parse filter arguments from command line."""
    filters: dict[str, str] = {}
    if not arg:
        return filters

    # Split by spaces but keep quoted strings together
    parts = shlex.split(arg)

    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            filters[key] = value

    return filters


def extract_url_parameters(url: str) -> tuple[str, dict[str, str]]:
    """Extract base URL and parameters from a URL."""
    base_url = url
    url_params = {}

    if '?' in url:
        base_url, query_string = url.split('?', 1)
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                url_params[key] = value

    return base_url, url_params


def format_json_content(content: str, title: str, border_style: str = 'green') -> None:
    """Format and display JSON content with syntax highlighting."""
    try:
        body_json = json.loads(content)
        json_str = json.dumps(body_json, indent=2)
        syntax = Syntax(json_str, 'json', theme='ansi_light', background_color='default', word_wrap=True)
        console.print(Panel(syntax, title=title, border_style=border_style))
    except json.JSONDecodeError:
        console.print(Panel(content, title=title, border_style=border_style))


def extract_endpoints(logs_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract endpoint information from logs data, grouped by the 'name' field."""
    endpoints: dict[str, dict[str, Any]] = {}
    console.print('[bold cyan]Extracting endpoints...[/bold cyan]')

    for data in logs_data.values():
        # Each file is a single request
        if not isinstance(data, dict):
            continue
        full_url = data.get('url', 'unknown')
        endpoint = extract_path_from_url(full_url)

        # Get the name field from the request body or use endpoint as fallback
        name = 'unknown'
        request_body = data.get('requestBody', '')
        if request_body:
            try:
                body_json = json.loads(request_body)
                if isinstance(body_json, dict):
                    name = body_json.get('name', endpoint)
            except json.JSONDecodeError:
                name = endpoint
        else:
            name = endpoint

        if name not in endpoints:
            endpoints[name] = {
                'status_codes': set(),
                'coverage': set(),
                'response_lengths': [],
                'content_types': set(),
                'requesters': set(),
                'methods': set(),
                'full_url': full_url,  # Store the full URL for reference
                'endpoints': set(),  # Store all endpoints associated with this name
            }

        # Extract data from the request
        status_code = data.get('inferredStatusCode', 'unknown')
        if status_code is not None:
            endpoints[name]['status_codes'].add(status_code)
        else:
            endpoints[name]['status_codes'].add('unknown')
        endpoints[name]['coverage'].add(data.get('coverage', 'unknown'))
        endpoints[name]['response_lengths'].append(len(str(data.get('responseBody', ''))))
        endpoints[name]['methods'].add(data.get('method', 'unknown'))
        endpoints[name]['endpoints'].add(endpoint)  # Add the endpoint to the set

        # Extract content type from response headers
        content_type = 'unknown'
        response_headers = data.get('responseHeaders', [])
        if isinstance(response_headers, list):
            for header in response_headers:
                if isinstance(header, dict) and header.get('name', '').lower() == 'content-type':
                    # Get the first value from the values array
                    values = header.get('values', [])
                    if values and len(values) > 0:
                        content_type = values[0]
                    break

        endpoints[name]['content_types'].add(content_type)

        # Add requester
        endpoints[name]['requesters'].add(data.get('requester', 'unknown'))

    return endpoints


def extract_request_parameters(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract all request parameters (URL, headers, body) from a request."""
    parameters = []

    # Get URL parameters
    url = data.get('url', '')
    if '?' in url:
        query_string = url.split('?')[1]
        params = query_string.split('&')
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                parameters.append((key, value))

    # Get request headers
    request_headers = data.get('requestHeaders', [])
    if isinstance(request_headers, list):
        for header in request_headers:
            if isinstance(header, dict):
                name = header.get('name', '')
                values = header.get('values', [])
                if values:
                    parameters.append((f'Header: {name}', values[0]))

    # Get request body if present
    request_body = data.get('requestBody', '')
    if request_body:
        try:
            body_json = json.loads(request_body)
            for key, value in body_json.items():
                parameters.append((f'Body: {key}', str(value)))
        except json.JSONDecodeError:
            parameters.append(('Body', request_body))

    return parameters


def extract_request_info(data: dict[str, Any]) -> list[str]:
    """Extract request information from data."""
    request_info = []

    # Add URL and method
    url = data.get('url', 'unknown')
    method = data.get('method', 'unknown')

    # Extract URL parameters if present
    base_url, url_params = extract_url_parameters(url)

    # Get requester
    requester = data.get('requester', 'unknown')

    request_info.append(f'[cyan]URL:[/cyan] {base_url}')
    # Add URL parameters if present
    if url_params:
        request_info.append('\n[bold cyan]URL Parameters:[/bold cyan]')
        for key, value in url_params.items():
            request_info.append(f'  [yellow]{key}:[/yellow] {value}')

    request_info.append('')  # Add a blank line for spacing

    request_info.append(f'[cyan]Method:[/cyan] {method} ')
    request_info.append(f'[cyan]Requester:[/cyan] {requester} ')

    # Add request headers
    request_headers = data.get('requestHeaders', [])
    if request_headers:
        request_info.append('\n[bold cyan]Request Headers:[/bold cyan]')
        for header in request_headers:
            if isinstance(header, dict):
                name = header.get('name', '')
                values = header.get('values', [])
                if values:
                    request_info.append(f'  [yellow]{name}:[/yellow] {values[0]}')

    return request_info


def extract_response_info(data: dict[str, Any]) -> list[str]:
    """Extract response information from data."""
    response_info = []

    # Add status code with description
    status_code = data.get('responseStatusCode', 'unknown')
    status_description = get_status_description(str(status_code))
    response_info.append(f'[cyan]Status Code:[/cyan] {status_code} ({status_description})')

    # Add duration if available
    duration = data.get('duration', 'unknown')
    if duration != 'unknown':
        # Format duration to 3 decimal places
        formatted_duration = f'{float(duration):.3f}'
        response_info.append(f'[cyan]Duration:[/cyan] {formatted_duration} s')

    # Add response headers
    response_headers = data.get('responseHeaders', [])
    if response_headers:
        response_info.append('\n[bold cyan]Response Headers:[/bold cyan]')
        for header in response_headers:
            if isinstance(header, dict):
                name = header.get('name', '')
                values = header.get('values', [])
                if values:
                    response_info.append(f'  [yellow]{name}:[/yellow] {values[0]}')

    return response_info
