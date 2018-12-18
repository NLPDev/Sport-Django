import json
import re

from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntryManager, LogEntry
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ObjectDoesNotExist, NON_FIELD_ERRORS
from django.db import transaction, DefaultConnectionProxy
from django.db.models import Model, QuerySet
from django.forms import forms
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.views.decorators.csrf import csrf_protect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.conf import settings as django_settings

from multidb_account.promocode.models import Promocode
from multidb_account.sport.models import Sport, ChosenSport
from multidb_account.assessment.models import AssessmentTopCategory, AssessmentTopCategoryPermission
from multidb_account.user.models import BaseCustomUser

csrf_protect_m = method_decorator(csrf_protect)
connection = DefaultConnectionProxy()

from multidb_account.promocode.models import Promocode
from multidb_account.sport.models import Sport, ChosenSport
from multidb_account.assessment.models import AssessmentTopCategory, AssessmentTopCategoryPermission
from multidb_account.user.models import BaseCustomUser

class CustomAdminSite(AdminSite):

    site_title = _('Personal Sport Record')

    site_header = site_title

    def each_context(self, request):
        """
        Returns a dictionary of variables to put in the template context for
        *every* page in the admin site.

        For sites running on a subpath, use the SCRIPT_NAME value if site_url
        hasn't been customized.
        """
        script_name = request.META['SCRIPT_NAME']
        site_url = script_name if self.site_url == '/' and script_name else self.site_url

        # Put localized_db into site_header
        if hasattr(request, 'localized_db') and request.user.is_authenticated():
            site_header = '{} <{}>.'.format(_('Current localized_db is'), get_localized_db().upper())
        else:
            site_header = self.site_header

        return {
            'site_title': self.site_title,
            'site_header': site_header,
            'site_url': site_url,
            'has_permission': self.has_permission(request),
            'available_apps': self.get_app_list(request),
        }

    def _build_app_dict(self, request, label=None):
        app_list = super(CustomAdminSite, self)._build_app_dict(request, label=label)

        if app_list.get('payment_gateway') is not None:
            app_list['payment_gateway']['models'][0]['nochange'] = True
            app_list['payment_gateway']['models'][1]['nochange'] = True

        return app_list


# Create site admin for every LOCALIZED_DATABASE
SITE_ADMINS = []
for db in django_settings.DATABASES:
    SITE_ADMINS.append({
        'name': db,
        'value': CustomAdminSite(name='admin_' + db)
    })


databases_expr = '|'.join(django_settings.DATABASES)
RE_ADMIN_LOCALIZED_DB = re.compile(r'/admin/(' + databases_expr + r')/')


def setattr_for_every_adminsite(attr, value):
    """
    Use:
        setattr_for_every_adminsite('login_form', CustomAuthenticationForm)
    Instead of:
        admin_site_ca.login_form = CustomAuthenticationForm
        admin_site_us.login_form = CustomAuthenticationForm
        admin_site_...
    """
    for site in SITE_ADMINS:
        site_admin = site['value']
        setattr(site_admin, attr, value)


def register_modeladmin_for_every_adminsite(model, model_admin):
    """
    Use:
        register_modeladmin_for_every_adminsite(BaseCustomUser, BaseCustomUserAdmin)
    Instead of:
        admin_site_ca.register(BaseCustomUser, BaseCustomUserAdmin)
        admin_site_us.register(BaseCustomUser, BaseCustomUserAdmin)
        admin_site_...
    """
    for site in SITE_ADMINS:
        site_admin = site['value']
        site_admin.register(model, model_admin)


def get_urlpattern_for_every_adminsite():
    """
    Use:
        get_urlpattern_for_every_adminsite()
    Instead of:
        [
            url(r'^admin/ca/', admin_site_ca.urls),
            url(r'^admin/us/', admin_site_us.urls),
            url(r'^admin/...
        ]
    """
    urls = []
    for site in SITE_ADMINS:
        site_name = site['name']
        site_admin = site['value']
        urls.append(url(r'^admin/{}/'.format(site_name), site_admin.urls))
    return urls


class CustomAuthenticationForm(AuthenticationForm):
    """ Login using `email` instead of 'username' """

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, email=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


setattr_for_every_adminsite('login_form', CustomAuthenticationForm)


class CustomLogEntryManager(LogEntryManager):
    """ Override log_action in order to create `.using(localized_db)` """

    def log_action(self, user_id, content_type_id, object_id, object_repr, action_flag, change_message='',
                   localized_db='default'):
        if isinstance(change_message, list):
            change_message = json.dumps(change_message)

        return self.model.objects.using(localized_db).create(
            user_id=user_id,
            content_type_id=content_type_id,
            object_id=force_text(object_id),
            object_repr=object_repr[:200],
            action_flag=action_flag,
            change_message=change_message,
        )


class CustomLogEntry(LogEntry):
    class Meta:
        proxy = True

    objects = CustomLogEntryManager()


def get_localized_db():
    from multidb_account.middleware import thread_locals
    return thread_locals.admin_show_localized_db


def delete_selected(modeladmin, request, queryset):

    if modeladmin.sync_databases:
        for db in django_settings.DATABASES.keys():
            queryset.using(db).delete()
    else:
        queryset.delete()

delete_selected.short_description = "Delete selected %(verbose_name_plural)s"


class MultiDBAdminMixin(object):
    sync_databases = None

    def get_actions(self, request):
        actions = super(MultiDBAdminMixin, self).get_actions(request)
        actions['delete_selected'] = (
            delete_selected, 'delete_selected',
            delete_selected.short_description
        )
        return actions

    @staticmethod
    def _is_staff_user_obj(obj):
        return isinstance(obj, BaseCustomUser) and obj.is_staff

    def save_model(self, request, obj, form, change):
        old_obj = type(obj).objects.using(obj._state.db).filter(pk=obj.pk).first()

        # Tell Django to save objects to the localized database.
        if self.sync_databases:
            for db_ in django_settings.DATABASES.keys():
                self._handle_promocode_updates(change, db_, obj, old_obj)

                if not change:
                    # On create, get max id from existing objects
                    latest_obj = type(obj).objects.using(db_).all().order_by('id').last()
                    if latest_obj:
                        obj.id = latest_obj.pk + 1

                obj.save(using=db_)
                self._handle_sport_creation(change, db_, obj)
        else:
            obj.save(using=get_localized_db())

    @staticmethod
    def _handle_sport_creation(change, db_, obj):
        if change or type(obj) != Sport:
            return

        # For each new Sport create related ChosenSport for every user
        users = get_user_model().objects.using(db_)
        chosen_sports = [ChosenSport(user=user, sport=obj) for user in users]
        ChosenSport.objects.using(db_).bulk_create(chosen_sports)

        MultiDBAdminMixin._create_assessment_top_category(obj, db_)

    @staticmethod
    def _handle_promocode_updates(change, db_, obj, old_obj):
        if not change or type(obj) != Promocode:
            return

        this_db_obj = type(obj).objects.using(db_).get(code=old_obj.code)
        obj.id = this_db_obj.pk

    @staticmethod
    def _create_assessment_top_category(sport, db_):
        asses_top_cat = AssessmentTopCategory.objects.using(db_).create(
            id=sport.id, name=sport.name, description=sport.description,
            sport=sport)

        MultiDBAdminMixin._handle_topcategory_creation(False, db_, asses_top_cat)

    @staticmethod
    def _handle_topcategory_creation(change, db_, obj):
        if change or type(obj) != AssessmentTopCategory:
            return

        # For each new AssessmentTopCategory create related A
        # AssessmentTopCategoryPermissions for every assessed assessor pair
        first_obj = AssessmentTopCategoryPermission.objects.using(db_).first()

        if first_obj is None:
            return

        all_permissions = AssessmentTopCategoryPermission.objects.using(db_)\
            .filter(assessment_top_category=first_obj.assessment_top_category)

        new_permissions = [
            AssessmentTopCategoryPermission(
                assessment_top_category=obj,
                assessor_has_access=False,
                assessed=permission.assessed,
                assessor=permission.assessor,

            ) for permission in all_permissions]

        AssessmentTopCategoryPermission.objects.using(db_).bulk_create(new_permissions)

    def delete_model(self, request, obj):
        # Tell Django to save objects to the localized database.
        if self.sync_databases:
            obj_id = obj.id
            for db in django_settings.DATABASES.keys():
                obj.delete(using=db)
                obj.id = obj_id
        else:
            obj.delete(using=get_localized_db())

    def save_related(self, request, form, formsets, change):
        """
        Given the ``HttpRequest``, the parent ``ModelForm`` instance, the
        list of inline formsets and a boolean value based on whether the
        parent is being added or changed, save the related objects to the
        database. Note that at this point save_form() and save_model() have
        already been called.
        """

        if self.sync_databases:
            for db in django_settings.DATABASES.keys():
                this_db_instance = form.instance.__class__.objects.db_manager(db).latest('id')

                if form.instance.pk != this_db_instance.pk:
                    try:
                        this_db_instance = form.instance.__class__.objects.db_manager(db).get(pk=form.instance.pk)
                    except ObjectDoesNotExist:
                        unique_field = self._get_unique_field(form.instance)
                        this_db_instance = form.instance.__class__.objects.db_manager(db) \
                            .get(**{unique_field: getattr(form.instance, unique_field)})

                form.instance = this_db_instance

                for key, item in form.cleaned_data.items():
                    if isinstance(item, QuerySet):
                        form.cleaned_data[key] = item.using(db)

                    if isinstance(item, Model):
                        item._state.db = db

                form.save_m2m()
        else:
            form.save_m2m()

        for formset in formsets:
            self.save_formset(request, form, formset, change=change)

    def _get_unique_field(self, obj):
        for field in obj._meta.fields:
            if field._unique:
                return field.name

    def get_queryset(self, request):
        # Tell Django to look for objects on the localized database.
        return super().get_queryset(request).using(get_localized_db())

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the localized database.
        return super().formfield_for_foreignkey(db_field, request, using=get_localized_db(), **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Tell Django to populate ManyToMany widgets using a query
        # on the localized database.
        return super().formfield_for_manytomany(db_field, request, using=get_localized_db(), **kwargs)

    @csrf_protect_m
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        with transaction.atomic(using=get_localized_db()):
            self.model._perform_unique_checks = _perform_unique_checks
            return self._changeform_view(request, object_id, form_url, extra_context)

    def log_addition(self, request, object, message):
        pass

    def log_change(self, request, object, message):
        pass

    def log_deletion(self, request, object, object_repr):
        pass


class MultiDBModelAdmin(MultiDBAdminMixin, admin.ModelAdmin):
    pass


class MultiDBTabularInline(admin.TabularInline):
    def get_queryset(self, request):
        # Tell Django to look for inline objects on the localized database.
        return super().get_queryset(request).using(get_localized_db())

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Tell Django to populate ForeignKey widgets using a query
        # on the localized database.
        return super().formfield_for_foreignkey(db_field, request, using=get_localized_db(), **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Tell Django to populate ManyToMany widgets using a query
        # on the localized database.
        return super().formfield_for_manytomany(db_field, request, using=get_localized_db(), **kwargs)


class ReadOnlyMixin(object):
    actions = None

    enable_change_view = False

    def get_list_display_links(self, request, list_display):
        """
        Return a sequence containing the fields to be displayed as links
        on the changelist. The list_display parameter is the list of fields
        returned by get_list_display().

        We override Django's default implementation to specify no links unless
        these are explicitly set.
        """
        if self.list_display_links or not list_display:
            return self.list_display_links
        else:
            return None,

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        The 'change' admin view for this model.

        We override this to redirect back to the changelist unless the view is
        specifically enabled by the "enable_change_view" property.
        """
        if self.enable_change_view:
            return super(ReadOnlyMixin, self).change_view(
                request,
                object_id,
                form_url,
                extra_context
            )
        else:
            opts = self.model._meta
            url = reverse('admin:{app}_{model}_changelist'.format(
                app=opts.app_label,
                model=opts.model_name,
            ))
            return HttpResponseRedirect(url)

    def changelist_view(self, request, extra_context=None):
        extra = extra_context or {}
        extra['title'] = ""
        return super(ReadOnlyMixin, self).changelist_view(request, extra_context=extra)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def get_localized_db_from_url(path):
    found = RE_ADMIN_LOCALIZED_DB.search(path)
    return found.groups(1)[0] if found else ''


# Monkey-patch to use `self._state.db` until this bug is fixed
# https://code.djangoproject.com/ticket/15130
def _perform_unique_checks(self, unique_checks):
    errors = {}

    for model_class, unique_check in unique_checks:
        # Try to look up an existing object with the same values as this
        # object's values for all the unique field.

        lookup_kwargs = {}
        for field_name in unique_check:
            f = self._meta.get_field(field_name)
            lookup_value = getattr(self, f.attname)
            # TODO: Handle multiple backends with different feature flags.
            if (lookup_value is None or
                    (lookup_value == '' and connection.features.interprets_empty_strings_as_nulls)):
                # no value, skip the lookup
                continue
            if f.primary_key and not self._state.adding:
                # no need to check for unique primary key when editing
                continue
            lookup_kwargs[str(field_name)] = lookup_value

        # some fields were skipped, no reason to do the check
        if len(unique_check) != len(lookup_kwargs):
            continue

        qs = model_class._default_manager.using(self._state.db).filter(**lookup_kwargs)

        # Exclude the current object from the query if we are editing an
        # instance (as opposed to creating a new one)
        # Note that we need to use the pk as defined by model_class, not
        # self.pk. These can be different fields because model inheritance
        # allows single model to have effectively multiple primary keys.
        # Refs #17615.
        model_class_pk = self._get_pk_val(model_class._meta)
        if not self._state.adding and model_class_pk is not None:
            qs = qs.exclude(pk=model_class_pk)
        if qs.exists():
            if len(unique_check) == 1:
                key = unique_check[0]
            else:
                key = NON_FIELD_ERRORS
            errors.setdefault(key, []).append(self.unique_error_message(model_class, unique_check))

    return errors
