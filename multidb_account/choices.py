from django.utils.translation import ugettext_lazy as _

from .constants import INVITE_PENDING, INVITE_ACCEPTED, INVITE_CANCELED, USER_TYPE_COACH, USER_TYPE_ATHLETE, \
    MEASURING_METRIC, MEASURING_IMPERIAL, TEAM_STATUS_ACTIVE, TEAM_STATUS_ARCHIVED, VIDEO_YOUTUBE, VIDEO_VIMEO, \
    USER_TYPE_ORG

USER_TYPES = (
    (USER_TYPE_COACH, _("Coach")),
    (USER_TYPE_ATHLETE, _("Athlete")),
    (USER_TYPE_ORG, _("Organisation")),
)

MEASURING = (
    (MEASURING_METRIC, _("Metric")),
    (MEASURING_IMPERIAL, _("Imperial")),
)

TEAM_STATUSES = (
    (TEAM_STATUS_ACTIVE, _("Active")),
    (TEAM_STATUS_ARCHIVED, _("Archived")),
)

INVITE_STATUSES = (
    (INVITE_PENDING, _("Pending")),
    (INVITE_ACCEPTED, _("Accepted")),
    (INVITE_CANCELED, _("Canceled")),
)

VIDEO_TYPES = (
    (VIDEO_YOUTUBE, _("Youtube")),
    (VIDEO_VIMEO, _("Vimeo")),
)

ORG_SIZES = (
    (0, '1-5'),
    (1, '6-50'),
    (2, '51-500'),
    (3, '501-1000'),
    (4, '1001+'),
)
