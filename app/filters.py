import re
from collections.abc import Callable
from typing import Any

from app.utils import clean_content_type


def _is_inverted_filter(filter_value: str) -> tuple[bool, str]:
    """Check if a filter is inverted (starts with !) and return the actual value."""
    if filter_value.startswith('!'):
        return True, filter_value[1:]
    return False, filter_value


def _apply_filter_with_inversion(filter_func: Callable, data: dict[str, Any], filter_value: str) -> bool:
    """Apply a filter function with support for inverted filters."""
    is_inverted, actual_value = _is_inverted_filter(filter_value)
    result = filter_func(data, actual_value)
    return not result if is_inverted else result


def _filter_by_method(data: dict[str, Any], method_filter: str) -> bool:
    """Filter by HTTP method."""
    return data.get('method', '').upper() == method_filter.upper()


def _filter_by_url(data: dict[str, Any], url_filter: str) -> bool:
    """Filter by URL pattern."""
    url = data.get('url', '')
    return bool(re.search(url_filter, url))


def _filter_by_operation(data: dict[str, Any], operation_filter: str) -> bool:
    """Filter by operation name."""
    operation = data.get('operationName', '')
    return operation_filter in operation


def _filter_by_status_code(data: dict[str, Any], status_filter: str) -> bool:
    """Filter by status code."""
    status_code = str(data.get('inferredStatusCode', ''))
    return status_code == status_filter


def _filter_by_scalar(data: dict[str, Any], scalar_filter: str) -> bool:
    """Filter by scalar type."""
    scalar = data.get('inferredScalarType', '')
    return scalar_filter in scalar


def _filter_by_coverage(data: dict[str, Any], coverage_filter: str) -> bool:
    """Filter by coverage."""
    coverage = data.get('coverage', '')
    return coverage_filter in coverage


def _filter_by_size(data: dict[str, Any], size_filter: str) -> bool:
    """Filter by response size range."""
    try:
        min_size, max_size = map(int, size_filter.split('-'))
        response_size = len(str(data.get('responseBody', '')))
        return min_size <= response_size <= max_size
    except (ValueError, TypeError):
        return True  # Invalid size format, ignore this filter


def _filter_by_content_type(data: dict[str, Any], content_type_filter: str) -> bool:
    """Filter by content type."""
    content_type = 'unknown'
    response_headers = data.get('responseHeaders', [])
    if isinstance(response_headers, list):
        for header in response_headers:
            if isinstance(header, dict) and header.get('name', '').lower() == 'content-type':
                values = header.get('values', [])
                if values and len(values) > 0:
                    content_type = clean_content_type(values[0])
                break
    return content_type_filter in content_type


def _filter_by_requester(data: dict[str, Any], requester_filter: str) -> bool:
    """Filter by requester."""
    requester = data.get('requester', '')
    return requester_filter in requester


def _filter_by_name(data: dict[str, Any], name_filter: str) -> bool:
    """Filter by endpoint name."""
    # Get the name field from the request body or use endpoint as fallback
    name = 'unknown'
    request_body = data.get('requestBody', '')
    if request_body:
        try:
            import json

            body_json = json.loads(request_body)
            name = body_json.get('name', '')
        except (json.JSONDecodeError, TypeError):
            pass

    # If name is still unknown, try to get it from the URL
    if name == 'unknown':
        from app.utils import extract_path_from_url

        name = extract_path_from_url(data.get('url', 'unknown'))

    return name_filter in name


def apply_filters(data: dict[str, Any], filters: dict[str, str]) -> bool:
    """Apply filters to a log entry and return True if it matches all filters."""
    if not filters:
        return True

    filter_functions = {
        'method': _filter_by_method,
        'url': _filter_by_url,
        'operation': _filter_by_operation,
        'status_code': _filter_by_status_code,
        'scalar': _filter_by_scalar,
        'coverage': _filter_by_coverage,
        'size': _filter_by_size,
        'content_type': _filter_by_content_type,
        'requester': _filter_by_requester,
        'endpoint': _filter_by_name,
    }

    for key, value in filters.items():
        if key in filter_functions and not _apply_filter_with_inversion(filter_functions[key], data, value):
            return False

    return True
