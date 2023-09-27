from typing import Optional

from pydantic_argparse.argparse.parser import ArgumentParser

from .model import CliArgs

from metaskingcli._version import __version__


def parse_arguments(
    program_args: Optional[list[str]] = None,
) -> tuple[ArgumentParser, CliArgs]:
    parser = ArgumentParser(
        model=CliArgs,
        prog="metask",
        description="meTasking CLI - Manage your work time logging from CLI",
        version=__version__,
    )
    args: CliArgs = parser.parse_typed_args(args=program_args)

    return parser, args
