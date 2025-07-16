"""Pydantic models for exchange data structure."""

from typing import Any

from pydantic import BaseModel, Field


class Header(BaseModel):
    """Model for HTTP headers."""

    name: str
    values: list[str]


class InferredScalar(BaseModel):
    """Model for inferred scalar values."""

    kind: str
    name: str
    confidence: float


class ExchangeData(BaseModel):
    """Main model for exchange data structure."""

    # Request information
    requestHeaders: list[Header]
    requestBody: str = ''

    # Response information
    responseHeaders: list[Header]
    responseBody: str
    responseStatusCode: int

    # Metadata
    scanId: str
    exchangeId: str
    method: str
    url: str
    curl: str
    duration: float

    # Coverage and status
    coverage: str
    user: str
    requester: str
    inferredStatusCode: int

    # Optional fields
    inferredScalars: list[InferredScalar] | None = None
    name: str | None = None

    class Config:
        """Pydantic configuration."""

        extra = 'allow'
        populate_by_name = True


class LogsData(BaseModel):
    """Model for the complete logs data structure."""

    data: dict[str, ExchangeData]

    @classmethod
    def from_dict(cls, data: dict[str, dict]) -> 'LogsData':
        """Create LogsData from a dictionary of raw JSON data."""
        processed_data = {}
        for filename, exchange_data in data.items():
            processed_data[filename] = ExchangeData(**exchange_data)
        return cls(data=processed_data)

    def get_exchange_data(self, filename: str) -> ExchangeData | None:
        """Get exchange data for a specific filename."""
        return self.data.get(filename)

    def get_all_filenames(self) -> list[str]:
        """Get all filenames in the logs data."""
        return list(self.data.keys())

    def count_files(self) -> int:
        """Count the number of files in the logs data."""
        return len(self.data)


class Filters(BaseModel):
    """Model for filter parameters."""

    method: str | None = None
    url: str | None = None
    operation: str | None = None
    status_code: str | None = None
    scalar: str | None = None
    coverage: str | None = None
    size: str | None = None
    content_type: str | None = None
    requester: str | None = None
    name: str | None = None

    @classmethod
    def from_dict(cls, filters_dict: dict[str, str]) -> 'Filters':
        """Create Filters from a dictionary."""
        return cls(**filters_dict)

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class EndpointInfo(BaseModel):
    """Model for endpoint information."""

    status_codes: set[int] = Field(default_factory=set)
    coverage: set[str] = Field(default_factory=set)
    response_lengths: list[int] = Field(default_factory=list)
    content_types: set[str] = Field(default_factory=set)
    requesters: set[str] = Field(default_factory=set)
    methods: set[str] = Field(default_factory=set)
    full_url: str
    endpoints: set[str] = Field(default_factory=set)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class EndpointsData(BaseModel):
    """Model for endpoints data structure."""

    endpoints: dict[str, EndpointInfo]

    @classmethod
    def from_dict(cls, endpoints_dict: dict[str, dict[str, Any]]) -> 'EndpointsData':
        """Create EndpointsData from a dictionary."""
        processed_endpoints = {}
        for name, data in endpoints_dict.items():
            processed_endpoints[name] = EndpointInfo(**data)
        return cls(endpoints=processed_endpoints)

    def get_endpoint_info(self, name: str) -> EndpointInfo | None:
        """Get endpoint info for a specific name."""
        return self.endpoints.get(name)

    def get_all_endpoint_names(self) -> list[str]:
        """Get all endpoint names."""
        return list(self.endpoints.keys())

    def count_endpoints(self) -> int:
        """Count the number of endpoints."""
        return len(self.endpoints)


class FileIndex(BaseModel):
    """Model for file indexing."""

    file_index: dict[int, str]
    index_file: dict[str, int]

    @classmethod
    def from_logs_data(cls, logs_data: LogsData) -> 'FileIndex':
        """Create FileIndex from LogsData."""
        filenames = sorted(logs_data.get_all_filenames())
        file_index = {i + 1: filename for i, filename in enumerate(filenames)}
        index_file = {filename: i + 1 for i, filename in enumerate(filenames)}
        return cls(file_index=file_index, index_file=index_file)


class GroupIds(BaseModel):
    """Model for group IDs."""

    group_ids: dict[str, str]

    @classmethod
    def generate(cls, endpoints: EndpointsData) -> 'GroupIds':
        """Generate group IDs for endpoints."""
        group_ids = {}
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        for current_id, name in enumerate(sorted(endpoints.get_all_endpoint_names())):
            # Generate ID (A, B, C, ..., Z, AA, AB, ...)
            id_str = ''
            temp_id = current_id
            while temp_id >= 0:
                id_str = alphabet[temp_id % 26] + id_str
                temp_id = temp_id // 26 - 1
            group_ids[name] = id_str

        return cls(group_ids=group_ids)


class RequestCounts(BaseModel):
    """Model for request counts."""

    request_counts: dict[str, int]
    filtered_groups: set[str]

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
