def activate(modeladmin, request, queryset):
    queryset.update(active=True)


def deactivate(modeladmin, request, queryset):
    queryset.update(active=False)


activate.short_description = "Mark selected promocodes as activated"
deactivate.short_description = "Mark selected promocodes as deactivated"
