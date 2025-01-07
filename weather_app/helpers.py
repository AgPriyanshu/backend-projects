from datetime import datetime

import pytz


def get_current_ist_date() -> str:
    # Get the IST timezone object
    ist_timezone = pytz.timezone("Asia/Kolkata")

    # Get the current time in IST
    ist_time = datetime.now(ist_timezone)

    return ist_time.strftime("%Y-%m-%d")
