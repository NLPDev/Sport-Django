from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite
from .admin_actions import activate, deactivate
from .models import Promocode


class PromocodeAdmin(MultiDBModelAdmin):
    change_list_template = 'promocode_list_form_template.html'
    sync_databases = True
    list_filter = ('active',)
    list_display = (
        'code', 'discount', 'name', 'end_date', 'active'
    )
    actions = (activate, deactivate)


register_modeladmin_for_every_adminsite(Promocode, PromocodeAdmin)
