from django.utils.translation import ugettext_lazy as _

PAYMENT_STATUS = (
    ('up_to_date', _("Up to date")),
    ('canceled', _("Canceled")),
    ('grace_period', _("Grace period")),
    ('locked_out', _("Locked out")),
    ('no_card', _("No card")),
    ('not_needed', _("Not needed")),
)
