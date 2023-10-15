from metaskingcli.args import CliArgs

from .app import init_app


def execute(args: CliArgs) -> int:
    assert args.tui is not None
    app = init_app(args.server, args.tui.read_only)
    app.run()
    return 0
