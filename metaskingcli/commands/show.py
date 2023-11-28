import sys
import json
import ruamel.yaml as yaml

from metaskingcli.args import CliArgs, OutputFormat
from metaskingcli.api.log import read


async def execute(args: CliArgs) -> int:
    assert args.show is not None
    log = await read(args.server, args.show.id)
    if args.show.format == OutputFormat.json:
        json.dump(log, sys.stdout)
    elif args.show.format == OutputFormat.yaml:
        y = yaml.YAML(typ="safe")
        y.default_flow_style = False
        y.dump([log], sys.stdout)
    else:
        time_range = ""
        if len(log['records']) > 0:
            time_range = f" ({log['records'][0]['start']} " + \
                f"- {log['records'][-1]['end']})"
        print(f"{log['id']}{time_range}: {log['name']}: {log['description']}")
    return 0
