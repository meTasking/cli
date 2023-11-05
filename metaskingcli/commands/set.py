from metaskingcli.args import CliArgs
from metaskingcli.api.log import update


async def execute(args: CliArgs) -> int:
    assert args.set is not None

    log = {}

    if args.set.category is not None:
        log["create_category"] = True
        log["category"] = args.set.category
    if args.set.task is not None:
        log["create_task"] = True
        log["task"] = args.set.task
    if args.set.name is not None:
        log["name"] = args.set.name
    if args.set.description is not None:
        log["description"] = args.set.description

    # Update the log
    await update(
        args.server,
        args.set.id,
        **log
    )
    return 0
