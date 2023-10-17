from datetime import datetime, date, timedelta

from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
)

from metaskingcli.args import CliArgs
from metaskingcli.api.log import list_all


def split_hours(hours: float) -> dict[str, str]:
    return {
        'all': f"{hours:.2f}",
        'hours': f"{hours:02.0f}",
        'minutes': f"{(hours * 60.0) % 60.0:02.0f}",
        'seconds': f"{(hours * 3600.0) % 60.0:02.0f}",
        'milliseconds': f"{(hours * 3600000.0) % 1000.0:04.0f}",
    }


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

    # This might be a bit overkill, but it's a good way to display the data
    # in a nice way. Using progress bars to display graph of time spent in
    # past days is not ideal, but it's better than no visualization at all.
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        TextColumn(" {task.fields[time][all]} "),
        BarColumn(bar_width=None),
        TextColumn(
            "  " +
            "{task.fields[time][hours]}h " +
            "{task.fields[time][minutes]}m " +
            "{task.fields[time][seconds]}s " +
            "{task.fields[time][milliseconds]}ms"
        ),
        auto_refresh=False,
    ) as days_as_progress:

        max_value = max(dates.values())
        min_date = min(dates.keys())
        max_date = max(dates.keys())
        cur_date = min_date
        while cur_date <= max_date:
            if cur_date in dates:
                value = dates[cur_date]
                # print(f"{cur_date.isoformat()}: {dates[cur_date]}")
            else:
                value = 0.0
                # print(f"{cur_date.isoformat()}: 0.0")
            days_as_progress.add_task(
                cur_date.isoformat(),
                total=round(max_value * 3600000.0),
                completed=round(value * 3600000.0),
                time=split_hours(value),
            )
            cur_date += timedelta(days=1)

        # print(f"Total: {total_duration}")
        days_as_progress.add_task(
            "Total",
            total=round(max_value * 3600000.0),
            completed=round(total_duration * 3600000.0),
            time=split_hours(total_duration),
        )

    return 0
