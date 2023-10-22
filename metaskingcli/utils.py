

def split_hours(hours: float | None) -> dict[str, str]:
    if hours is None:
        return {
            'all': '---.--',
            'hours': '---',
            'minutes': '--',
            'seconds': '--',
            'milliseconds': '----',
        }
    return {
        'all': f"{hours:03.2f}",
        'hours': f"{hours:03.0f}",
        'minutes': f"{(hours * 60.0) % 60.0:02.0f}",
        'seconds': f"{(hours * 3600.0) % 60.0:02.0f}",
        'milliseconds': f"{(hours * 3600000.0) % 1000.0:04.0f}",
    }
