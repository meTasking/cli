from metaskingcli.args import CliArgs
from metaskingcli.api.log import get_active, list_all


def execute(args: CliArgs) -> int:
    print("Active logs:")
    try:
        active = get_active(args.server)
        print(f"- {active['id']}: {active['name']}: {active['description']}")
    except Exception:
        print("- None")

    print("All non-stopped logs:")
    offset = 0
    logs = list_all(args.server, stopped=False, offset=offset)
    while len(logs) != 0:
        for log in logs:
            print(f"- {log['id']}: {log['name']}: {log['description']}")

        offset += len(logs)
        logs = list_all(args.server, stopped=False, offset=offset)

    return 0
