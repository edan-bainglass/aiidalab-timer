# -*- coding: utf-8 -*-

import logging
import subprocess
from datetime import timedelta
from pathlib import Path

import ipywidgets as ipw
import yaml
from aiida import load_profile
from IPython.display import Javascript, display

_ = load_profile()

TEMPLATE = """
    <div class="app-container">
        <div id="timer">{}</div>
    </div>
"""

logger = logging.getLogger(__name__)


def get_start_widget(appbase, jupbase, notebase):
    from aiidalab_widgets_base.utils.loaders import load_css

    load_css(Path(appbase) / "assets" / "styles")
    if not (lifetime := get_lifetime()):
        return ipw.HTML(TEMPLATE.format("Session lifetime not set"))
    return Timer(duration=lifetime)


def get_lifetime():
    try:
        config_file = Path.home() / ".aiidalab" / "aiidalab.yaml"
        if config_file.exists():
            with config_file.open() as file:
                config = yaml.safe_load(file)
                if "lifetime" in config:
                    hh, mm, ss = map(int, config.get("lifetime").split(":"))
                    return timedelta(hours=hh, minutes=mm, seconds=ss)
    except Exception as err:
        logger.error(f"Error while reading lifetime from config: {err}")
    return None


def get_container_uptime():
    process = subprocess.check_output(["ps", "-o", "etime=", "-p", "1"])
    elapsed_str = process.decode().strip()

    parts = list(map(int, reversed(elapsed_str.split(":"))))
    if len(parts) == 1:  # seconds only
        return timedelta(seconds=parts[0])
    elif len(parts) == 2:  # minutes:seconds
        return timedelta(minutes=parts[1], seconds=parts[0])
    elif len(parts) == 3:  # hours:minutes:seconds
        return timedelta(hours=parts[2], minutes=parts[1], seconds=parts[0])
    else:  # days-hours:minutes:seconds
        days, hms = parts[-1], parts[:-1]
        return timedelta(days=days, hours=hms[2], minutes=hms[1], seconds=hms[0])


class Timer(ipw.HTML):
    def __init__(self, duration, *args, **kwargs):
        self.duration = duration
        super().__init__(
            value=TEMPLATE.format(""),
            *args,
            **kwargs,
        )
        self.add_class("timer-widget")
        self.on_displayed(self.start_timer)

    def start_timer(self, *args):
        uptime = get_container_uptime()
        remaining = max(self.duration - uptime, timedelta(seconds=0))
        total_seconds = int(remaining.total_seconds())

        display(
            Javascript(f"""
              const timer = document.getElementById('timer');
              let timeLeft = {total_seconds};

              const formatTime = (seconds) => {{
                let hrs = Math.floor(seconds / 3600);
                let mins = Math.floor((seconds % 3600) / 60);
                let secs = seconds % 60;
                return `${{String(hrs).padStart(2, '0')}}:${{String(mins).padStart(2, '0')}}:${{String(secs).padStart(2, '0')}}`;
              }}

              const updateTimer = () => {{
                if (timeLeft < 1800) {{
                    timer.style.color = 'red';
                    timer.style.fontWeight = 'bold';
                }}
                if (timeLeft < 300) {{
                    timer.style.fontSize = '2em';
                    timer.style.fontWeight = 'normal';
                    timer.style.maxWidth = '80%';
                    timer.innerHTML = `
                        <p>⚠️ AiiDAlab container shutdown imminent ⚠️</p>
                        <br>
                        <p>Please save your work using either the <b>Terminal</b> or the <b>File Manager</b></p>
                    `;
                }} else {{
                    timer.innerHTML = 'Time remaining: ' + formatTime(timeLeft);
                    timeLeft--;
                    setTimeout(updateTimer, 1000);
                }}
              }}

              updateTimer();
            """)
        )
