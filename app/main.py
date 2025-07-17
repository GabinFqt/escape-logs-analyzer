from pathlib import Path

import click

from app.processor import process_zip, start_shell


@click.group()
def main() -> None:
    """Escape scan debugger CLI tool."""


@main.command()
@click.argument('zip_file', type=click.Path(exists=True, file_okay=True, dir_okay=False))
def analyze(zip_file: str) -> None:
    """Analyze logs from a zip file."""
    zip_path = Path(zip_file)
    if zip_path.suffix != '.zip':
        click.echo('Error: File must be a zip file', err=True)
        return

    logs_data = process_zip(zip_path)
    start_shell(logs_data)


if __name__ == '__main__':
    main()
