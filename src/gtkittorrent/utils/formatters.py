import datetime
import math

def format_bytes(num_bytes, precision=1, binary=True):
    """Format bytes into human-readable string (KiB, MiB, GiB, etc.)."""
    if not isinstance(num_bytes, (int, float)) or num_bytes < 0:
        return "0 B"
    
    base = 1024.0 if binary else 1000.0
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'] if binary else ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    val = float(num_bytes)
    for unit in units[:-1]:
        if abs(val) < base:
            if unit == 'B':
                return f"{int(val)} B"
            return f"{val:.{precision}f} {unit}"
        val /= base
    return f"{val:.{precision}f} {units[-1]}"

def format_speed(speed_bytes_sec):
    """Format speed in bytes per second."""
    if not isinstance(speed_bytes_sec, (int, float)) or speed_bytes_sec <= 0:
        return "0 B/s"
    return f"{format_bytes(speed_bytes_sec, precision=1)}/s"

def format_eta(seconds):
    """Format ETA in seconds into human-readable format like '1h 23m' or '∞'."""
    # qBittorrent returns 8640000 (100 days) for unknown/infinite ETA
    if not isinstance(seconds, (int, float)) or seconds < 0 or seconds >= 8640000:
        return "∞"
    if seconds == 0:
        return "0s"
    
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def format_timestamp(timestamp):
    """Format unix epoch timestamp to localized date/time string."""
    if not isinstance(timestamp, (int, float)) or timestamp <= 0:
        return "—"
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "—"

def format_duration(seconds):
    """Format elapsed or active duration."""
    if not isinstance(seconds, (int, float)) or seconds <= 0:
        return "—"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"

def format_ratio(ratio):
    """Format share ratio."""
    if not isinstance(ratio, (int, float)) or ratio < 0:
        return "—"
    if ratio >= 10000:
        return "∞"
    return f"{ratio:.2f}"

def format_percent(progress):
    """Format float (0.0 to 1.0) into percentage string."""
    if not isinstance(progress, (int, float)):
        return "0.0%"
    return f"{progress * 100:.1f}%"

STATE_MAP = {
    'error': ("Errored", "dialog-error-symbolic"),
    'missingFiles': ("Missing files", "dialog-warning-symbolic"),
    'uploading': ("Seeding", "network-transmit-receive-symbolic"),
    'pausedUP': ("Completed (paused)", "emblem-ok-symbolic"),
    'stoppedUP': ("Completed (stopped)", "emblem-ok-symbolic"),
    'queuedUP': ("Queued for upload", "appointment-soon-symbolic"),
    'stalledUP': ("Seeding (stalled)", "network-idle-symbolic"),
    'checkingUP': ("Checking upload", "system-run-symbolic"),
    'forcedUP': ("[F] Seeding", "network-transmit-receive-symbolic"),
    'allocating': ("Allocating disk space", "drive-harddisk-symbolic"),
    'downloading': ("Downloading", "folder-download-symbolic"),
    'metaDL': ("Fetching metadata", "network-transmit-receive-symbolic"),
    'pausedDL': ("Paused", "media-playback-pause-symbolic"),
    'stoppedDL': ("Stopped", "media-playback-stop-symbolic"),
    'queuedDL': ("Queued", "appointment-soon-symbolic"),
    'stalledDL': ("Stalled", "network-idle-symbolic"),
    'checkingDL': ("Checking download", "system-run-symbolic"),
    'forcedDL': ("[F] Downloading", "folder-download-symbolic"),
    'checkingResumeData': ("Checking resume data", "system-run-symbolic"),
    'moving': ("Moving storage", "document-save-as-symbolic"),
    'unknown': ("Unknown", "dialog-information-symbolic")
}

def get_state_display(state):
    """Return (display_name, icon_name) for a torrent state."""
    return STATE_MAP.get(state, (state or "Unknown", "dialog-information-symbolic"))
