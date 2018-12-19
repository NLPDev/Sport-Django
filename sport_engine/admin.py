from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite
from .models import SportEngineTeam, SportEngineGame, SportEngineEvent


class SportEngineBaseAdmin(MultiDBModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SportEngineTeamAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id', 'team')


class SportEngineGameAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id',)


class SportEngineEventAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id', 'sport_engine_team', 'sport_engine_game')





class SportEngineTeamAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id', 'team')


class SportEngineGameAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id',)


class SportEngineEventAdmin(SportEngineBaseAdmin):
    list_display = ('sport_engine_id', 'sport_engine_team', 'sport_engine_game')

register_modeladmin_for_every_adminsite(SportEngineTeam, SportEngineTeamAdmin)
register_modeladmin_for_every_adminsite(SportEngineGame, SportEngineGameAdmin)
register_modeladmin_for_every_adminsite(SportEngineEvent, SportEngineEventAdmin)
