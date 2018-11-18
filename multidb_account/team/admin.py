from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite
from .models import Team


class TeamAdmin(MultiDBModelAdmin):

    list_display = (
        'name', 'status', 'team_picture', 'organisation', 'sport'
    )


register_modeladmin_for_every_adminsite(Team, TeamAdmin)
