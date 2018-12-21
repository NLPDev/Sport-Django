from multidb_account.admin import MultiDBModelAdmin, register_modeladmin_for_every_adminsite

from .models import HelpCenterReport, OrganisationSupport


class HelpCenterReportAdmin(MultiDBModelAdmin):
    sync_databases = True
    list_display = ('organization', 'coach_name', 'date', 'date_created', 'details', 'name', 'owner')
    list_select_related = ['owner']

    def has_add_permission(self, request):
        return False

    @staticmethod
    def has_delete_permission(request, obj=None, **kwargs):
        return False



class HelpCenterReportAdmin(MultiDBModelAdmin):
    sync_databases = True
    list_display = ('organization', 'coach_name', 'date', 'date_created', 'details', 'name', 'owner')
    list_select_related = ['owner']

    def has_add_permission(self, request):
        return False

    @staticmethod
    def has_delete_permission(request, obj=None, **kwargs):
        return False


class OrganisationSupportAdmin(MultiDBModelAdmin):
    sync_databases = True
    list_display = ('date_created', 'organisation', 'name', 'email', 'phone_number', 'support_type', 'owner')
    list_select_related = ('organisation', 'owner')

    def has_add_permission(self, request):
        return False

    @staticmethod
    def has_delete_permission(request, obj=None, **kwargs):
        return False


register_modeladmin_for_every_adminsite(HelpCenterReport, HelpCenterReportAdmin)
register_modeladmin_for_every_adminsite(OrganisationSupport, OrganisationSupportAdmin)
