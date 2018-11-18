from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite
from .models import Sport


class SportAdmin(MultiDBModelAdmin):

    sync_databases = True

    list_display = (
        'name', 'is_available', 'description'
    )


register_modeladmin_for_every_adminsite(Sport, SportAdmin)