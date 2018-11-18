from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite
from .models import Invite


class InviteAdmin(MultiDBModelAdmin):

    list_display = (
        'requester', 'team', 'date_sent',
        'status', 'recipient_type', 'recipient'
    )

register_modeladmin_for_every_adminsite(Invite, InviteAdmin)
