import re
from collections.abc import Callable
from http import HTTPMethod

from app.models import Exchange, Filters, LogsData, PathName


def _filter_by_method(exchange: Exchange, method_filter: HTTPMethod) -> bool:
    """Filter by HTTP method."""
    return exchange.method == method_filter


def _filter_by_url(exchange: Exchange, url_filter: str) -> bool:
    """Filter by URL pattern."""
    return bool(re.search(url_filter, exchange.url))


def _filter_by_status_code(exchange: Exchange, status_filter: str) -> bool:
    """Filter by status code."""
    return str(exchange.inferredStatusCode) == status_filter


def _filter_by_coverage(exchange: Exchange, coverage_filter: str) -> bool:
    """Filter by coverage."""
    return coverage_filter in exchange.coverage


def _filter_by_size(exchange: Exchange, size_filter: str) -> bool:
    """Filter by response size range."""
    try:
        min_size, max_size = map(int, size_filter.split('-'))
        response_size = len(str(exchange.responseBody))
        return min_size <= response_size <= max_size
    except (ValueError, TypeError):
        return True  # Invalid size format, ignore this filter


def _filter_by_content_type(exchange: Exchange, content_type_filter: str) -> bool:
    """Filter by content type."""
    return content_type_filter in exchange.content_type if exchange.content_type else False


def _filter_by_requester(exchange: Exchange, requester_filter: str) -> bool:
    """Filter by requester."""
    return requester_filter in exchange.requester


def _filter_by_path(exchange: Exchange, path_filter: PathName) -> bool:
    """Filter by endpoint name."""
    return exchange.path == path_filter


def _filter_by_in_schema(exchange: Exchange, in_schema_filter: bool) -> bool:
    """Filter by in schema."""
    return exchange.in_schema == bool(in_schema_filter)


def _apply_filters_on_exchange(exchange: Exchange, filters: Filters) -> bool:
    """Apply filters to a log entry and return True if it matches all filters."""

    def _is_inverted_filter(filter_value: str) -> tuple[bool, str]:
        """Check if a filter is inverted (starts with !) and return the actual value."""
        return (True, filter_value[1:]) if filter_value.startswith('!') else (False, filter_value)

    def _apply_filter_with_inversion(filter_func: Callable, data: Exchange, filter_value: str) -> bool:
        """Apply a filter function with support for inverted filters."""
        is_inverted, actual_value = _is_inverted_filter(filter_value)
        result = filter_func(data, actual_value)
        return not result if is_inverted else result

    if filters.method and not _apply_filter_with_inversion(_filter_by_method, exchange, filters.method):
        return False
    if filters.url and not _apply_filter_with_inversion(_filter_by_url, exchange, filters.url):
        return False
    if filters.status_code and not _apply_filter_with_inversion(_filter_by_status_code, exchange, filters.status_code):
        return False
    if filters.inferred_status_code and not _apply_filter_with_inversion(_filter_by_status_code, exchange, filters.inferred_status_code):
        return False
    if filters.coverage and not _apply_filter_with_inversion(_filter_by_coverage, exchange, filters.coverage):
        return False
    if filters.size and not _apply_filter_with_inversion(_filter_by_size, exchange, filters.size):
        return False
    if filters.content_type and not _apply_filter_with_inversion(_filter_by_content_type, exchange, filters.content_type):
        return False
    if filters.requester and not _apply_filter_with_inversion(_filter_by_requester, exchange, filters.requester):
        return False
    if filters.path and not _apply_filter_with_inversion(_filter_by_path, exchange, filters.path):
        return False
    if filters.in_schema is not None and not _apply_filter_with_inversion(_filter_by_in_schema, exchange, str(filters.in_schema)):
        return False

    return True


def apply_filters(filters: Filters, logs_data: LogsData) -> LogsData:
    """Apply filters to the logs data."""
    log_data = LogsData()
    for exchange in logs_data.get_all_exchanges():
        if _apply_filters_on_exchange(exchange, filters):
            log_data.add_exchange(exchange)
    return log_data
