import json

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


def clean_content_type(content_type: str) -> str:
    """Clean content type by removing charset for application/json."""
    return 'application/json' if content_type.startswith('application/json') else content_type


def bytes_to_kb(bytes_size: int) -> str:
    """Convert bytes to KB with 2 decimal places."""
    return f'{bytes_size / 1024:.2f} KB'


def get_status_description(status_code: str) -> str:
    """Get a human-readable description for an HTTP status code."""
    return HTTP_STATUS_DESCRIPTIONS.get(status_code, 'Unknown')


def format_json_content(content: str, title: str, border_style: str = 'green') -> None:
    """Format and display JSON content with syntax highlighting."""
    try:
        body_json = json.loads(content)
        json_str = json.dumps(body_json, indent=2)
        syntax = Syntax(json_str, 'json', theme='ansi_light', background_color='default', word_wrap=True)
        console.print(Panel(syntax, title=title, border_style=border_style))
    except json.JSONDecodeError:
        console.print(Panel(content, title=title, border_style=border_style))


