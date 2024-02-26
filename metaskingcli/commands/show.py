import sys
import json
from datetime import datetime
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
        time_spent = 0
        if len(log['records']) > 0:
            time_range = f" ({log['records'][0]['start']} " + \
                f"- {log['records'][-1]['end']})"

        for record in log['records']:
            if record['end'] is not None:
                start = datetime.fromisoformat(record['start'])
                end = datetime.fromisoformat(record['end'])
                time_spent += (end - start).total_seconds() / 3600.0

        print(
            f"{log['id']} {time_spent:.2f}h{time_range}: " +
            f"{log['name']}: {log['description']}"
        )
    return 0
