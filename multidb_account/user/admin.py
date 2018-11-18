from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from multidb_account.admin import (
    MultiDBTabularInline,
    MultiDBAdminMixin,
    register_modeladmin_for_every_adminsite,
    MultiDBModelAdmin)
from multidb_account.admin.common import get_localized_db
from multidb_account.assessment.models import Assessment
from multidb_account.sport.models import ChosenSport
from .forms import OrganisationForm, UserCreationForm, UserChangeForm
from .models import BaseCustomUser, Organisation


class ChosenSportInline(MultiDBTabularInline):
    model = ChosenSport

    readonly_fields = ('sport', 'date_joined',)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class CustomUserByPromocodeListFilter(SimpleListFilter):
    title = _('promocode')
    parameter_name = 'promocode'

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.using(get_localized_db()) \
            .values_list('athleteuser__promocode', flat=True) \
            .distinct()
        from_db = [(x, x) for x in qs if x]
        any_nonempty = [('any-non-empty', 'Any non-empty')]
        return any_nonempty + from_db

    def queryset(self, request, qs):
        filter_val = self.value()
        if filter_val:
            if filter_val == 'any-non-empty':
                qs = qs.exclude(Q(athleteuser__promocode=None) | Q(athleteuser__promocode=''))
            else:
                qs = qs.filter(athleteuser__promocode=filter_val)
        return qs


class CustomUserByOrganisationListFilter(SimpleListFilter):
    title = _('organisation')
    parameter_name = 'organisation'

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.using(get_localized_db()) \
            .values_list('member_of_organisations__pk', 'member_of_organisations__name') \
            .distinct()
        return [(x[0], x[1]) for x in qs if x[0]]

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.filter(organisation=self.value())
        return queryset


class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('user_type', 'chosensport__sport',
                   CustomUserByPromocodeListFilter,
                   CustomUserByOrganisationListFilter)
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('jwt_last_expired', 'date_joined', 'last_login')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'user_type'),
        }),
    )


class MultiDBUserAdmin(MultiDBAdminMixin, CustomUserAdmin):
    pass


class BaseCustomUserAdmin(MultiDBUserAdmin):
    list_display = ('id', 'email', 'user_type', 'province_or_state', 'city', 'first_name', 'last_name', 'get_sports',
                    'promocode')
    list_display_links = list_display
    inlines = ()
    fieldsets = ()
    exclude = []

    def get_sports(self, obj):
        return ', '.join(
            [s.sport.name for s in obj.chosensport_set.using(obj.country or 'default').filter(is_chosen=True)])

    def promocode(self, obj):
        return obj.athleteuser.promocode if hasattr(obj, 'athleteuser') else ''

    promocode.admin_order_field = 'athleteuser__promocode'

    def add_view(self, *args, **kwargs):
        self.inlines = ()
        return super().add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.inlines = (ChosenSportInline,)
        return super().change_view(*args, **kwargs)

    def save_model(self, request, obj, form, change):
        # Tweak some fields before creating new instance
        if not change:
            obj.country = get_localized_db()
            obj.is_active = False
            obj.is_superuser = obj.is_staff

        super().save_model(request, obj, form, change)

        # Send confirmation email after user creation
        if not change:
            obj.send_confirm_account_email()

    get_sports.short_description = 'Chosen sports'


register_modeladmin_for_every_adminsite(BaseCustomUser, BaseCustomUserAdmin)


class OrganisationAdmin(MultiDBModelAdmin):
    list_display = ('name', 'size', 'sports')
    list_display_links = list_display
    list_filter = []
    inlines = ()
    ordering = ()
    readonly_fields = ()
    filter_horizontal = ('login_users', 'members', 'own_assessments')
    fieldsets = ()
    exclude = ()
    form = OrganisationForm

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'own_assessments':
            kwargs['queryset'] = Assessment.objects.using(get_localized_db()) \
                .exclude(is_public_everywhere=True) \
                .order_by('parent_sub_category', 'name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


register_modeladmin_for_every_adminsite(Organisation, OrganisationAdmin)
