"""Commands module for processing zip files and starting the shell."""

import json
import zipfile
from http import HTTPMethod
from pathlib import Path

from rich.panel import Panel

from app.models import Exchange, ExchangeId, ExchangeParameter, InferredScalar, LogsData, ParamLocation, PathName
from app.utils import console


def process_zip(zip_path: Path) -> LogsData:
    """Process zip file and return logs data as LogsData model."""
    logs_data = LogsData()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            try:
                if file_name.endswith('.json'):
                    with zip_ref.open(file_name) as f:
                        exchange_json = json.load(f)
                        logs_data.add_exchange(
                            Exchange(
                                exchangeId=ExchangeId(file_name),
                                path=PathName(exchange_json['name']),
                                user=exchange_json['user'],
                                requester=exchange_json['requester'],
                                inferredStatusCode=exchange_json['inferredStatusCode'],
                                inferredScalars=[
                                    InferredScalar(
                                        name=scalar['name'], kind=scalar['kind'], confidence=scalar['confidence']
                                    )
                                    for scalar in exchange_json['inferredScalars']
                                ],
                                # in_schema=exchange_json['in_schema'],
                                requestHeaders=[
                                    ExchangeParameter(
                                        name=header['name'], values=header['values'], _in=ParamLocation.HEADER
                                    )
                                    for header in exchange_json['requestHeaders']
                                ],
                                requestBody=exchange_json['requestBody'],
                                method=HTTPMethod(exchange_json['method'].upper()),
                                url=exchange_json['url'],
                                responseHeaders=[
                                    ExchangeParameter(
                                        name=header['name'], values=header['values'], _in=ParamLocation.HEADER
                                    )
                                    for header in exchange_json['responseHeaders']
                                ],
                                responseBody=exchange_json['responseBody'],
                                responseStatusCode=exchange_json['responseStatusCode'],
                                scanId=exchange_json['scanId'],
                                curl=exchange_json['curl'],
                                duration=exchange_json['duration'],
                                coverage=exchange_json['coverage'],
                            )
                        )
            except Exception as e:
                console.print(f'[bold red]Error processing {file_name}: {e}[/bold red]')
                continue
    console.print(
        Panel(f'[green]Successfully decompressed {len(logs_data)} JSON files[/green]', title='Zip Processing'),
    )
    return logs_data


def start_shell(logs_data: LogsData) -> None:
    """Start the interactive shell with the processed logs data."""
    from app.commands.base import LogShell

    LogShell(logs_data).cmdloop()
