"""Commands module for processing zip files and starting the shell."""

import json
import zipfile
from pathlib import Path

from rich.panel import Panel

from app.models import LogsData
from app.utils import console


def process_zip(zip_path: Path) -> LogsData:
    """Process zip file and return logs data as LogsData model."""
    logs_data = {}
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.json'):
                with zip_ref.open(file_name) as f:
                    logs_data[file_name] = json.load(f)
    console.print(
        Panel(f'[green]Successfully decompressed {len(logs_data)} JSON files[/green]', title='Zip Processing'),
    )
    return LogsData.from_dict(logs_data)


def start_shell(logs_data: LogsData) -> None:
    """Start the interactive shell with the processed logs data."""
    from app.commands.base import LogShell

    LogShell(logs_data).cmdloop()
