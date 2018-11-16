from .utils import get_customer_from_localized_databases
from .models import Event
from .signals import (
    cancelled,
    card_changed,
    subscription_made,
    webhook_processing_error,
    WEBHOOK_SIGNALS,
)


def webhook_event_handler(event_data):
    cus_id = None
    global event
    customer_crud_events = [
        "customer.created",
        "customer.updated",
        "customer.deleted"
    ]

    event_type = event_data.get('type', None)

    if event_type in customer_crud_events:
        cus_id = event_data["data"]["object"]["id"]
    else:
        cus_id = event_data["data"]["object"].get("customer", None)

    if cus_id:
        # We need to query DBs to get the customer's country because Stripe webhooks are not authenticated
        customer = get_customer_from_localized_databases(cus_id)

        if customer:
            event = Event.objects.using(customer.athlete.user.country).create(
                stripe_id=event_data.get('id', None),
                type=event_type,
                livemode=event_data.get('livemode', None),
                customer=customer
            )

            signal = WEBHOOK_SIGNALS.get(event_type)
            if signal:
                signal.send(instance=customer, sender=None, event_data=event_data)

            event.processed = True
            event.save()
            return event
        else:
            return None
    else:
        return None
