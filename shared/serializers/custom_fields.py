from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework.fields import Field

from .constants import RecentTimePeriod


class TimePeriodField(Field):
    default_error_messages = {
        "invalid_format": _(
            "The time_period parameter must be either one of the following strings: 'last_week', 'last_month', 'last_3_months', or a list containing exactly two date strings, e.g. [01-01-1999, '01-01-2024']."
        ),
        "invalid_date_range": _("Start date must be before or equal to end date."),
    }

    def to_internal_value(self, data):
        try:
            parsed_period_array = data.split(",")
            if len(parsed_period_array) < 2:
                parsed_period = parsed_period_array[0]
            elif len(parsed_period_array) == 2:
                parsed_period = parsed_period_array
            else:
                raise SyntaxError()

            if isinstance(parsed_period, str) and RecentTimePeriod.validate(
                parsed_period
            ):
                return RecentTimePeriod.get_enum(parsed_period)

            elif isinstance(parsed_period, list) and len(parsed_period) == 2:
                date_format = "%d-%m-%Y"
                start_date = datetime.strptime(parsed_period[0], date_format)
                end_date = datetime.strptime(parsed_period[1], date_format)

                if start_date > end_date:
                    self.fail("invalid_date_range")

                return (
                    start_date,
                    end_date,
                )
            else:
                self.fail("invalid_format")

        except (ValueError, SyntaxError):
            self.fail("invalid_format")

        return super().to_internal_value(data)

    def to_representation(self, value):
        return super().to_representation(value)
