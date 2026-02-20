import click
from .commands import copy, search, analyze, generate_receipt_cmd, generate_from_json


@click.group()
def cli():
    """Файловый менеджер с генерацией квитанций."""
    pass


cli.add_command(copy)
cli.add_command(search)
cli.add_command(analyze)
cli.add_command(generate_receipt_cmd)
cli.add_command(generate_from_json)
