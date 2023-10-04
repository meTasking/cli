from metaskingcli.args import CliArgs
from metaskingcli.api.log import start


def execute(args: CliArgs) -> int:
    assert args.start is not None

    json_params = {}
    if args.start.name is not None:
        json_params['name'] = args.start.name
    if args.start.description is not None:
        json_params['description'] = args.start.description
    if args.start.task is not None:
        json_params['task'] = args.start.task
    if args.start.category is not None:
        json_params['category'] = args.start.category

    start(args.server, **json_params)
    return 0
