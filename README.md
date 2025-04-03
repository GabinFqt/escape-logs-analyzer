# Escape Logs Analyzer

A command-line tool for analyzing and filtering log files from Escape.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/escape-logs-analyzer.git
cd escape-logs-analyzer

# Install dependencies
make install
```

## Usage

```bash
# Start the analyzer with a specific log file
make run file=your_log_file.zip

# Or directly with Python
python -m app.main your_log_file.zip
```

## Available Commands

- `list [filters]`: List all requests with their details
- `info <number/filename> [filters] [--no-body]`: Show information about a specific file
  - You can display multiple files: `info 1 2 3 4`
  - Use `--no-body` to hide request and response bodies
- `count [filters]`: Count the number of requests
- `summary [full] [filters]`: Show a summary of all endpoints
- `params <number/filename> [filters]`: Show request parameters for a specific file
- `help`: Show this help message
- `quit` or `q`: Exit the shell

## Filters

Filters can be specified as key=value pairs:

- `method=GET`: Filter by HTTP method
- `status_code=200`: Filter by status code
- `content_type=application/json`: Filter by content type
- `requester=oracle`: Filter by requester
- `size=100-1000`: Filter by response size range
- `url=api/users`: Filter by URL pattern
- `operation=login`: Filter by operation name
- `coverage=covered`: Filter by coverage status
- `endpoint=/users`: Filter by endpoint name

You can invert any filter by adding a `!` prefix:

- `method=!GET`: All methods except GET
- `status_code=!200`: All status codes except 200
- `content_type=!application/json`: All content types except application/json
