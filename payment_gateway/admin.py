from multidb_account.admin import MultiDBModelAdmin, ReadOnlyMixin, register_modeladmin_for_every_adminsite
from .models import Customer, Event


class CustomerAdmin(ReadOnlyMixin, MultiDBModelAdmin):
    list_display = (
        'athlete', 'last_update', 'payment_status', 'last_payment_date',
        'grace_period_start', 'grace_period_end'
    )

    readonly_fields = list_display + ('stripe_id', 'created_at')

    list_filter = ('payment_status', 'last_payment_date')


class EventAdmin(ReadOnlyMixin, MultiDBModelAdmin):

    list_display = (
        'stripe_id', 'created_at', 'customer', 'type', 'livemode', 'processed',
    )


register_modeladmin_for_every_adminsite(Customer, CustomerAdmin)
register_modeladmin_for_every_adminsite(Event, EventAdmin)
