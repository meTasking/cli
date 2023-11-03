import math


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
        'hours': f"{math.floor(hours):03d}",
        'minutes': f"{math.floor((hours * 60.0) % 60.0):02d}",
        'seconds': f"{math.floor((hours * 3600.0) % 60.0):02d}",
        'milliseconds': f"{math.floor((hours * 3600000.0) % 1000.0):03.0f}",
    }
