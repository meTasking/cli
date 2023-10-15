from metaskingcli.args import CliArgs
from metaskingcli.api.log import get_active, list_all


def execute(args: CliArgs) -> int:
    print("Active logs:")
    active = get_active(args.server)
    if active is not None:
        time_range = ""
        if len(active['records']) > 0:
            time_range = f" ({active['records'][0]['start']} " + \
                f"- {active['records'][-1]['end']})"
        print(
            f"{active['id']}{time_range}: " +
            f"{active['name']}: {active['description']}"
        )
    else:
        print("- None")

    print("All non-stopped logs:")
    offset = 0
    logs = list_all(args.server, stopped=False, offset=offset)
    while len(logs) != 0:
        for log in logs:
            time_range = ""
            if len(log['records']) > 0:
                time_range = f" ({log['records'][0]['start']} " + \
                    f"- {log['records'][-1]['end']})"
            print(
                f"{log['id']}{time_range}: " +
                f"{log['name']}: {log['description']}"
            )

        offset += len(logs)
        logs = list_all(args.server, stopped=False, offset=offset)

    return 0
