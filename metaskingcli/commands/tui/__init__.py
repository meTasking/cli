from metaskingcli.args import CliArgs

from .app import init_app


async def execute(args: CliArgs) -> int:
    assert args.tui is not None
    app = init_app(
        args.server,
        args.tui.read_only,
        args.tui.category,
        args.tui.task,
    )
    await app.run_async()
    return 0
