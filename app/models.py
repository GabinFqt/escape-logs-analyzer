"""Pydantic models for exchange data structure."""

import enum
import json
import shlex
from http import HTTPMethod
from typing import NewType

from pydantic import BaseModel, Field

from app.utils import console

PathName = NewType('PathName', str)
ExchangeId = NewType('ExchangeId', str)


class ParamLocation(enum.StrEnum):
    """Model for parameter location."""

    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    BODY = 'body'


class ExchangeParameter(BaseModel):
    """Model for HTTP headers."""

    name: str
    values: list[str]
    _in: ParamLocation


class InferredScalar(BaseModel):
    """Model for inferred scalar values."""

    kind: str
    name: str
    confidence: float


class Filters(BaseModel):
    """Model for filter parameters."""

    method: str | None = Field(default=None)
    url: str | None = Field(default=None)
    status_code: str | None = Field(default=None)
    inferred_status_code: str | None = Field(default=None)
    coverage: str | None = Field(default=None)
    size: str | None = Field(default=None)
    content_type: str | None = Field(default=None)
    requester: str | None = Field(default=None)
    path: PathName | None = Field(default=None)

    def at_least_one_filter(self) -> bool:
        """Check if at least one filter is set."""
        return any(getattr(self, field) is not None for field in self.model_fields)

    @staticmethod
    def from_arg(arg: str) -> 'Filters':
        """Parse filter arguments from command line."""
        filters = Filters()
        parts = shlex.split(arg)

        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                if key in filters.model_fields:
                    setattr(filters, key, value)
                else:
                    console.print(
                        f'[bold red]Ignoring invalid filter: {key}[/bold red]. Valid filters are: {filters.model_fields.keys()}'
                    )

        return filters


class Exchange(BaseModel):
    """Main model for exchange data structure."""

    exchangeId: ExchangeId
    path: PathName

    # Request information
    requestHeaders: list[ExchangeParameter]
    requestBody: str | None
    method: HTTPMethod
    url: str

    # Response information
    responseHeaders: list[ExchangeParameter]
    responseBody: str
    responseStatusCode: int

    # Metadata
    scanId: str
    curl: str
    duration: float

    # Coverage and status
    coverage: str
    user: str
    requester: str
    inferredStatusCode: int

    inferredScalars: list[InferredScalar]
    in_schema: bool

    @property
    def queryParams(self) -> list[ExchangeParameter]:
        """Get the parameters in the path."""
        return [
            ExchangeParameter(name=param.split('=')[0], values=[param.split('=')[1]], _in=ParamLocation.QUERY)
            for param in self.url.split('?')[1].split('&')
            if '=' in param
        ]

    @property
    def pathParams(self) -> list[ExchangeParameter]:
        """Get the parameters in the path using OpenAPI Spec format."""
        import re

        # Extract path parameters from the URL using OpenAPI format {paramName}
        path_params = []

        # Find all path parameters in the URL (e.g., /users/{userId}/posts/{postId})
        # We need to match the actual values from the URL against the path template
        url_parts = self.url.split('?')[0].split('/')  # Remove query params
        path_parts = self.path.split('/')

        # Match URL parts with path template parts
        min_length = min(len(url_parts), len(path_parts))
        for i in range(min_length):
            url_part = url_parts[i]
            path_part = path_parts[i]

            # Check if this path part is a parameter (contains {paramName})
            param_match = re.search(r'\{([^}]+)\}', path_part)
            if param_match:
                param_name = param_match.group(1)
                param_value = url_part
                path_params.append(ExchangeParameter(name=param_name, values=[param_value], _in=ParamLocation.PATH))

        return path_params

    @property
    def content_type(self) -> str | None:
        """Get the content type of the response."""
        for header in self.responseHeaders:
            if header.name.lower() == 'content-type':
                if 'application/json' in header.values:
                    return 'application/json'
                return ', '.join(header.values)
        return None

    @property
    def responseBodyJson(self) -> dict | None:
        """Get the body as a JSON object."""
        try:
            return json.loads(self.responseBody)
        except json.JSONDecodeError:
            return None


class LogsData(BaseModel):
    """Model for the complete logs data structure."""

    data: dict[ExchangeId, Exchange] = Field(default_factory=dict)

    def __len__(self) -> int:
        """Get the number of exchanges in the logs data."""
        return len(self.data)

    def add_exchange(self, exchange: Exchange) -> None:
        """Add an exchange to the logs data."""
        self.data[exchange.exchangeId] = exchange

    def get_exchange_by_id(self, exchange_id: ExchangeId) -> Exchange | None:
        """Get exchange data for a specific exchange ID."""
        try:
            return self.data[exchange_id]
        except KeyError:
            console.print(f'[bold red]Exchange ID {exchange_id} not found[/bold red]')
            return None

    def get_all_exchange_ids(self) -> set[ExchangeId]:
        """Get all exchange IDs in the logs data."""
        return set(self.data.keys())

    def get_all_exchanges(self) -> list[Exchange]:
        """Get all exchanges in the logs data."""
        return list(self.data.values())

    def count_exchanges(self) -> int:
        """Count the number of exchanges in the logs data."""
        return len(self.data)


class EndpointInfo(BaseModel):
    """Model for endpoint information."""

    path: PathName
    method: HTTPMethod

    status_codes: set[int] = Field(default_factory=set)
    inferred_status_codes: set[int] = Field(default_factory=set)
    coverage: set[str] = Field(default_factory=set)
    response_lengths: list[int] = Field(default_factory=list)
    content_types: set[str] = Field(default_factory=set)
    requesters: set[str] = Field(default_factory=set)
    methods: set[str] = Field(default_factory=set)
    urls: set[str] = Field(default_factory=set)

    exchange_ids: set[ExchangeId] = Field(default_factory=set)

    @property
    def count_exchanges(self) -> int:
        """Count the number of exchanges in the endpoint information."""
        return len(self.exchange_ids)


class EndpointsInfoData(BaseModel):
    """Model for endpoint information data."""

    data: dict[tuple[PathName, HTTPMethod], EndpointInfo] = Field(default_factory=dict)

    def __len__(self) -> int:
        """Get the number of endpoint information in the data."""
        return len(self.data)

    def add_exchange(self, exchange: Exchange) -> None:
        """Add an exchange to the endpoint information data."""
        if (exchange.path, exchange.method) not in self.data:
            self.data[(exchange.path, exchange.method)] = EndpointInfo(path=exchange.path, method=exchange.method)
        self.data[(exchange.path, exchange.method)].exchange_ids.add(exchange.exchangeId)
        self.data[(exchange.path, exchange.method)].status_codes.add(exchange.responseStatusCode)
        self.data[(exchange.path, exchange.method)].inferred_status_codes.add(exchange.inferredStatusCode)
        self.data[(exchange.path, exchange.method)].coverage.add(exchange.coverage)
        self.data[(exchange.path, exchange.method)].response_lengths.append(len(exchange.responseBody))
        if exchange.content_type:
            self.data[(exchange.path, exchange.method)].content_types.add(exchange.content_type)
        self.data[(exchange.path, exchange.method)].requesters.add(exchange.requester)
        self.data[(exchange.path, exchange.method)].methods.add(exchange.method)

    def get_endpoint_info(self, path: PathName, method: HTTPMethod) -> EndpointInfo | None:
        """Get endpoint information for a specific path and method."""
        return self.data.get((path, method))

    def get_all_endpoints(self) -> list[EndpointInfo]:
        """Get all endpoint information in the data."""
        return list(self.data.values())

    def get_all_endpoint_paths(self) -> set[tuple[PathName, HTTPMethod]]:
        """Get all endpoint paths in the data."""
        return set(self.data.keys())

    @classmethod
    def from_logs_data(cls, logs_data: 'LogsData') -> 'EndpointsInfoData':
        """Create EndpointsInfoData from LogsData."""
        endpoints_info_data = cls()
        for exchange in logs_data.get_all_exchanges():
            endpoints_info_data.add_exchange(exchange)
        return endpoints_info_data
