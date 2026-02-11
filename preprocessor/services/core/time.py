class TimeFormatter:

    @staticmethod
    def format_hms(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        return f'{hours}:{minutes:02d}:{secs:02d}'

    @staticmethod
    def format_human(seconds: float) -> str:
        if seconds < 60:
            return f'{seconds:.1f}s'
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f'{minutes}m {secs}s'
        hours = minutes // 60
        minutes = minutes % 60
        return f'{hours}h {minutes}m {secs}s'
