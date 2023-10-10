from datetime import datetime, date, timedelta

from metaskingcli.args import CliArgs
from metaskingcli.api.log import list_all


def execute(args: CliArgs) -> int:
    assert args.report is not None

    dates: dict[date, float] = {}

    total_duration = 0.0

    offset = 0
    while True:
        logs = list_all(
            args.server,
            offset=offset,
            flags=args.report.flags,
            since=args.report.since,
            until=args.report.until,
        )

        if len(logs) == 0:
            break
        offset += len(logs)

        for log in logs:
            for record in log['records']:
                if record['end'] is None:
                    continue

                start = datetime.fromisoformat(record['start'])
                end = datetime.fromisoformat(record['end'])
                start_date = start.date()
                day_duration = 0.0
                if start_date in dates:
                    day_duration = dates[start_date]
                record_duration = (end - start).total_seconds() / 3600.0
                total_duration += record_duration
                day_duration += record_duration
                dates[start_date] = day_duration

    min_date = min(dates.keys())
    max_date = max(dates.keys())
    cur_date = min_date
    while cur_date <= max_date:
        if cur_date in dates:
            print(f"{cur_date.isoformat()}: {dates[cur_date]}")
        else:
            print(f"{cur_date.isoformat()}: 0.0")
        cur_date += timedelta(days=1)

    print(f"Total: {total_duration}")

    return 0
