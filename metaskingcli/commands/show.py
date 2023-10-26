import json
import ruamel.yaml as yaml

from metaskingcli.args import CliArgs, OutputFormat
from metaskingcli.api.log import read


async def execute(args: CliArgs) -> int:
    assert args.show is not None
    log = await read(args.server, args.show.id)
    if args.show.format == OutputFormat.json:
        print(json.dumps(log))
    elif args.show.format == OutputFormat.yaml:
        print(yaml.dump([log]))
    else:
        time_range = ""
        if len(log['records']) > 0:
            time_range = f" ({log['records'][0]['start']} " + \
                f"- {log['records'][-1]['end']})"
        print(f"{log['id']}{time_range}: {log['name']}: {log['description']}")
    return 0
