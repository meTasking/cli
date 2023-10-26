import json
import ruamel.yaml as yaml

from metaskingcli.args import CliArgs, OutputFormat
from metaskingcli.api.log import list_all


async def execute(args: CliArgs) -> int:
    assert args.list is not None

    async for log in list_all(
        args.server,
        flags=args.list.flags,
        order=args.list.order,
        since=args.list.since,
        until=args.list.until,
    ):
        if args.list.format == OutputFormat.json:
            print(json.dumps(log))
        elif args.list.format == OutputFormat.yaml:
            print(yaml.dump([log]))
        else:
            time_range = ""
            if len(log['records']) > 0:
                time_range = f" ({log['records'][0]['start']} " + \
                    f"- {log['records'][-1]['end']})"
            print(
                f"{log['id']}{time_range}: " +
                f"{log['name']}: {log['description']}"
            )

    return 0
