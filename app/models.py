"""Pydantic models for exchange data structure."""

from pydantic import BaseModel


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
        # Allow extra fields that might be present in the data
        extra = 'allow'
        # Use field names as they appear in the JSON
        populate_by_name = True


class LogsData(BaseModel):
    """Model for the complete logs data structure."""

    # Dictionary mapping filename to ExchangeData
    # This is a wrapper around Dict[str, ExchangeData] for better typing
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
