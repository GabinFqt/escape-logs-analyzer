import json
import shlex
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from app.models import (
    EndpointsData,
    ExchangeData,
    Filters,
    LogsData,
    RequestInfo,
    RequestParameters,
    ResponseInfo,
    UrlParameters,
)

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


def parse_filters(arg: str) -> Filters:
    """Parse filter arguments from command line."""
    filters_dict: dict[str, str] = {}
    if not arg:
        return Filters()

    # Split by spaces but keep quoted strings together
    parts = shlex.split(arg)

    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            filters_dict[key] = value

    return Filters.from_dict(filters_dict)


def extract_url_parameters(url: str) -> UrlParameters:
    """Extract base URL and parameters from a URL."""
    base_url = url
    url_params = {}

    if '?' in url:
        base_url, query_string = url.split('?', 1)
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                url_params[key] = value

    return UrlParameters(base_url=base_url, parameters=url_params)


def format_json_content(content: str, title: str, border_style: str = 'green') -> None:
    """Format and display JSON content with syntax highlighting."""
    try:
        body_json = json.loads(content)
        json_str = json.dumps(body_json, indent=2)
        syntax = Syntax(json_str, 'json', theme='ansi_light', background_color='default', word_wrap=True)
        console.print(Panel(syntax, title=title, border_style=border_style))
    except json.JSONDecodeError:
        console.print(Panel(content, title=title, border_style=border_style))


def extract_endpoints(logs_data: LogsData) -> EndpointsData:
    """Extract endpoint information from logs data, grouped by the 'name' field."""
    endpoints_dict: dict[str, dict[str, Any]] = {}
    console.print('[bold cyan]Extracting endpoints...[/bold cyan]')

    for data in logs_data.data.values():
        # Each file is a single request
        full_url = data.url
        endpoint = data.name or 'unknown'

        if endpoint not in endpoints_dict:
            endpoints_dict[endpoint] = {
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
        status_code = data.inferredStatusCode
        endpoints_dict[endpoint]['status_codes'].add(status_code)
        endpoints_dict[endpoint]['coverage'].add(data.coverage)
        endpoints_dict[endpoint]['response_lengths'].append(len(str(data.responseBody)))
        endpoints_dict[endpoint]['methods'].add(data.method)
        endpoints_dict[endpoint]['endpoints'].add(endpoint)  # Add the endpoint to the set

        # Extract content type from response headers
        content_type = 'unknown'
        for header in data.responseHeaders:
            if header.name.lower() == 'content-type' and header.values:
                content_type = header.values[0]
                break

        endpoints_dict[endpoint]['content_types'].add(content_type)

        # Add requester
        endpoints_dict[endpoint]['requesters'].add(data.requester)

    return EndpointsData.from_dict(endpoints_dict)


def extract_request_parameters(data: ExchangeData) -> RequestParameters:
    """Extract all request parameters (URL, headers, body) from a request."""
    url_params = []
    headers = []
    body_params = []

    # Get URL parameters
    url = data.url
    if '?' in url:
        query_string = url.split('?')[1]
        params = query_string.split('&')
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                url_params.append((key, value))

    # Get request headers
    for header in data.requestHeaders:
        if header.values:
            headers.append((f'Header: {header.name}', header.values[0]))

    # Get request body if present
    request_body = data.requestBody
    if request_body:
        try:
            body_json = json.loads(request_body)
            for key, value in body_json.items():
                body_params.append((f'Body: {key}', str(value)))
        except json.JSONDecodeError:
            body_params.append(('Body', request_body))

    return RequestParameters(url_params=url_params, headers=headers, body_params=body_params)


def extract_request_info(data: ExchangeData) -> RequestInfo:
    """Extract request information from data."""
    # Extract URL parameters if present
    url_params = extract_url_parameters(data.url)

    return RequestInfo(
        url=data.url,
        method=data.method,
        requester=data.requester,
        url_parameters=url_params,
        headers=data.requestHeaders,
    )


def extract_response_info(data: ExchangeData) -> ResponseInfo:
    """Extract response information from data."""
    status_description = get_status_description(str(data.responseStatusCode))

    return ResponseInfo(
        status_code=data.responseStatusCode,
        status_description=status_description,
        duration=data.duration,
        headers=data.responseHeaders,
    )
