from django.db.models.functions import Coalesce

from multidb_account.admin import (
    MultiDBModelAdmin,
    register_modeladmin_for_every_adminsite,
    get_localized_db,
    MultiDBTabularInline
)
from .forms import AssessmentAdminForm
from .models import (
    Assessment,
    AssessmentSubCategory,
    AssessmentTopCategory,
    AssessmentFormat
)


class AssessmentAdmin(MultiDBModelAdmin):
    sync_databases = True
    list_display = ('name', 'parent_sub_category', 'description', 'is_public_everywhere', 'format', 'is_private')
    list_filter = ('parent_sub_category', 'is_private')
    change_form_template = 'assessment_change_form_template.html'
    form = AssessmentAdminForm

    # Special sorting rules for the `parent_sub_category` related field
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'parent_sub_category':
            qs_all = AssessmentSubCategory.objects.using(get_localized_db())
            qs_to_sort = qs_all.annotate(to_sort=Coalesce('parent_sub_category__parent_top_category__name',
                                                          'parent_top_category__name',
                                                          'parent_sub_category__name'))
            qs = qs_to_sort.order_by('to_sort')
            kwargs['queryset'] = qs

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if 'relationship_types' in form.cleaned_data:
            form.instance.relationship_types.add(*list(form.cleaned_data['relationship_types']))


class AssessmentSubCategoryAdmin(MultiDBModelAdmin):
    sync_databases = True

    list_display = ('name', 'description', 'parent_top_category', 'parent_sub_category')

    list_filter = ('parent_sub_category', 'parent_top_category')


class AssessmentTopCategoryAdmin(MultiDBModelAdmin):
    sync_databases = True

    list_display = ('name', 'sport')


class AssessmentRelationshipTypeAdmin(MultiDBModelAdmin):
    sync_databases = True

    list_display = ('type', 'description',)


class AssessmentFormatAdmin(MultiDBModelAdmin):
    sync_databases = True

    list_display = ('unit', 'description', 'validation_regex')

    def has_delete_permission(self, request, obj=None):
        return False


register_modeladmin_for_every_adminsite(AssessmentFormat, AssessmentFormatAdmin)
register_modeladmin_for_every_adminsite(Assessment, AssessmentAdmin)
register_modeladmin_for_every_adminsite(AssessmentSubCategory, AssessmentSubCategoryAdmin)
register_modeladmin_for_every_adminsite(AssessmentTopCategory, AssessmentTopCategoryAdmin)



