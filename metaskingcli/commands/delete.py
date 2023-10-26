from metaskingcli.args import CliArgs
from metaskingcli.api.log import delete


async def execute(args: CliArgs) -> int:
    assert args.delete is not None
    await delete(
        args.server,
        args.delete.id if args.delete.id is not None else -1
    )
    return 0
