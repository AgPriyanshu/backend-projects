from datetime import timedelta
from enum import StrEnum
from typing import Type

from dateutil.relativedelta import relativedelta
from django.utils import timezone


class RecentTimePeriod(StrEnum):
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_6_MONTHS = "last_3_months"

    @classmethod
    def validate(cls, value: str) -> bool:
        """Check if the given value is a valid enum value."""
        return value in {member.value for member in cls}

    @classmethod
    def get_enum(cls, value: str):
        """
        Retrieves the enum member corresponding to the given value.
        """
        for member in cls:
            if member.value == value:
                return member
        return None

    @classmethod
    def get_date_range(cls, value: Type["RecentTimePeriod"]):
        match value:
            case RecentTimePeriod.LAST_WEEK:
                today = timezone.now()
                start_date = today - relativedelta(weeks=1)
                end_date = today - timedelta(days=1)
                return (
                    start_date,
                    end_date,
                )

            case RecentTimePeriod.LAST_MONTH:
                today = timezone.now()
                start_date = today - relativedelta(months=1)
                end_date = today - timedelta(days=1)
                return (
                    start_date,
                    end_date,
                )

            case RecentTimePeriod.LAST_6_MONTHS:
                today = timezone.now()
                start_date = today - relativedelta(months=6)
                end_date = today - timedelta(days=1)
                return (
                    start_date,
                    end_date,
                )

            case _:
                return None
