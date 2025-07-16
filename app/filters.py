import re
from collections.abc import Callable

from app.models import ExchangeData, Filters
from app.utils import clean_content_type


def _is_inverted_filter(filter_value: str) -> tuple[bool, str]:
    """Check if a filter is inverted (starts with !) and return the actual value."""
    if filter_value.startswith('!'):
        return True, filter_value[1:]
    return False, filter_value


def _apply_filter_with_inversion(filter_func: Callable, data: ExchangeData, filter_value: str) -> bool:
    """Apply a filter function with support for inverted filters."""
    is_inverted, actual_value = _is_inverted_filter(filter_value)
    result = filter_func(data, actual_value)
    return not result if is_inverted else result


def _filter_by_method(data: ExchangeData, method_filter: str) -> bool:
    """Filter by HTTP method."""
    return data.method.upper() == method_filter.upper()


def _filter_by_url(data: ExchangeData, url_filter: str) -> bool:
    """Filter by URL pattern."""
    return bool(re.search(url_filter, data.url))


def _filter_by_status_code(data: ExchangeData, status_filter: str) -> bool:
    """Filter by status code."""
    status_code = str(data.inferredStatusCode)
    return status_code == status_filter


def _filter_by_coverage(data: ExchangeData, coverage_filter: str) -> bool:
    """Filter by coverage."""
    return coverage_filter in data.coverage


def _filter_by_size(data: ExchangeData, size_filter: str) -> bool:
    """Filter by response size range."""
    try:
        min_size, max_size = map(int, size_filter.split('-'))
        response_size = len(str(data.responseBody))
        return min_size <= response_size <= max_size
    except (ValueError, TypeError):
        return True  # Invalid size format, ignore this filter


def _filter_by_content_type(data: ExchangeData, content_type_filter: str) -> bool:
    """Filter by content type."""
    content_type = 'unknown'
    for header in data.responseHeaders:
        if header.name.lower() == 'content-type' and header.values:
            content_type = clean_content_type(header.values[0])
            break
    return content_type_filter in content_type


def _filter_by_requester(data: ExchangeData, requester_filter: str) -> bool:
    """Filter by requester."""
    return requester_filter in data.requester


def _filter_by_name(data: ExchangeData, name_filter: str) -> bool:
    """Filter by endpoint name."""
    name = data.name or ''
    return name_filter in name


def apply_filters(data: ExchangeData, filters: Filters) -> bool:
    """Apply filters to a log entry and return True if it matches all filters."""
    if not filters.to_dict():
        return True

    filter_functions = {
        'method': _filter_by_method,
        'url': _filter_by_url,
        'status_code': _filter_by_status_code,
        'coverage': _filter_by_coverage,
        'size': _filter_by_size,
        'content_type': _filter_by_content_type,
        'requester': _filter_by_requester,
        'endpoint': _filter_by_name,
    }

    for key, value in filters.to_dict().items():
        if key in filter_functions and not _apply_filter_with_inversion(filter_functions[key], data, value):
            return False

    return True
