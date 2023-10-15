import sys
import logging

from .args import parse_arguments
from .commands import (
    cmd_tui,
    cmd_start,
    cmd_next,
    cmd_pause,
    cmd_resume,
    cmd_stop,
    cmd_status,
    cmd_show,
    cmd_list,
    cmd_report,
    cmd_delete,
    cmd_edit,
)

root_log = logging.getLogger()
log = logging.getLogger(__name__)


def setup_log() -> logging.Handler:
    root_log.setLevel(logging.DEBUG)

    root_stderr_handler = logging.StreamHandler(stream=sys.stderr)
    root_stderr_handler.setLevel(logging.INFO)
    basic_formatter = logging.Formatter(
        "%(asctime)s\t-\t%(name)s\t-\t%(levelname)s\t-\t%(message)s"
    )
    root_stderr_handler.setFormatter(basic_formatter)
    root_log.addHandler(root_stderr_handler)
    return root_stderr_handler


def main():
    # Configure logging
    root_log_handler = setup_log()

    parser, args = parse_arguments()

    # Apply logging related arguments
    if args.verbose:
        root_log_handler.setLevel(logging.DEBUG)

    code = 0
    if args.help:
        parser.print_help()
    elif args.tui:
        code = cmd_tui(args)
    elif args.start:
        code = cmd_start(args)
    elif args.next:
        code = cmd_next(args)
    elif args.pause:
        code = cmd_pause(args)
    elif args.resume:
        code = cmd_resume(args)
    elif args.stop:
        code = cmd_stop(args)
    elif args.status:
        code = cmd_status(args)
    elif args.show:
        code = cmd_show(args)
    elif args.list:
        code = cmd_list(args)
    elif args.report:
        code = cmd_report(args)
    elif args.delete:
        code = cmd_delete(args)
    elif args.edit:
        code = cmd_edit(args)

    sys.exit(code)
