import sys
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
        category=args.list.category,
        task=args.list.task,
        description=args.list.description,
        since=args.list.since,
        until=args.list.until,
    ):
        if args.list.format == OutputFormat.json:
            json.dump(log, sys.stdout)
        elif args.list.format == OutputFormat.yaml:
            y = yaml.YAML(typ="safe")
            y.default_flow_style = False
            y.dump([log], sys.stdout)
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
