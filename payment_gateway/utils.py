from django.conf import settings
from payment_gateway.models import Customer, Event


def get_customer_from_localized_databases(customer_stripe_id):
    # This function locates and returns a customer object if exists in a localized database.
    customer_found = False
    global customer

    debug = getattr(settings, 'DEBUG', False)
    localized_databases = getattr(settings, 'LOCALIZED_DATABASES', None)
    for database in localized_databases:
        try:
            customer = Customer.objects.using(database).get(stripe_id=customer_stripe_id)
            customer_found = True
        except Customer.DoesNotExist:
            if debug:
                print("DEBUG: multidb_auth_backend -- Customer NOT found in database: " + database)
            customer = None

        if customer_found:
            if debug:
                print("DEBUG: multidb_auth_backend -- Customer found in database: " + database)
            break

    if customer_found:
        return customer
    else:
        return None


def get_event_from_localized_databases(event_id):
    # This function locates and returns an event object if exists in a localized database.
    event_found = False
    global event

    debug = getattr(settings, 'DEBUG', False)
    localized_databases = getattr(settings, 'LOCALIZED_DATABASES', None)
    for database in localized_databases:
        try:
            event = Event.objects.using(database).get(stripe_id=event_id)
            event_found = True
        except Event.DoesNotExist:
            if debug:
                print("DEBUG: multidb_auth_backend -- Event NOT found in database: " + database)

        if event_found:
            if debug:
                print("DEBUG: multidb_auth_backend -- Event found in database: " + database)
            break

    if event_found:
        return event
    else:
        return None
