from functools import partial

from shared.constants import AppName
from shared.notifications import send_notification

send_notification = partial(send_notification, app_name=AppName.WEB_GIS)
