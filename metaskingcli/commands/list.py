import json
import ruamel.yaml as yaml

from metaskingcli.args import CliArgs, OutputFormat
from metaskingcli.api.log import list_all


def execute(args: CliArgs) -> int:
    assert args.list is not None

    offset = 0
    logs = list_all(args.server, offset=offset)
    while len(logs) != 0:
        for log in logs:
            if args.list.format == OutputFormat.json:
                print(json.dumps(log))
            elif args.list.format == OutputFormat.yaml:
                print(yaml.dump([log]))
            else:
                print(f"{log['id']}: {log['name']}: {log['description']}")

        offset += len(logs)
        logs = list_all(args.server, offset=offset)

    return 0
