import json
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from . import settings as app_settings
from .models import Event
from .utils import get_event_from_localized_databases
import stripe


class SubscriptionSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=app_settings.PLANS_CHOICES, required=True)

    def validate_plan(self, plan):
        """
        Check plan is valid.
        """
        if plan not in app_settings.PLANS_CHOICES:
            raise serializers.ValidationError(_("Plan is not valid"))
        return plan


class CardSerializer(serializers.Serializer):
    address_city = serializers.CharField(read_only=True)
    address_country = serializers.CharField(read_only=True)
    address_line1 = serializers.CharField(read_only=True)
    address_line2 = serializers.CharField(read_only=True)
    address_state = serializers.CharField(read_only=True)
    address_zip = serializers.CharField(read_only=True)
    brand = serializers.CharField(read_only=True)
    last4 = serializers.CharField(read_only=True)
    exp_month = serializers.CharField(read_only=True)
    exp_year = serializers.CharField(read_only=True)
    cardholder_name = serializers.CharField(source='name', read_only=True)


class CardTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class WebhookSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, allow_null=False)
    type = serializers.CharField(required=True, allow_null=False)
    livemode = serializers.BooleanField(required=True)
    data = serializers.JSONField(required=True, allow_null=False)

    def validate(self, data):
        event_id = data.get('id', None)
        event_type = data.get('type', None)

        if get_event_from_localized_databases(event_id):
            raise serializers.ValidationError({"error":  _("Duplicate Event")})

        if event_id and event_type:
            evt = stripe.Event.retrieve(event_id)
            stripe_event = json.loads(
                json.dumps(
                    evt.to_dict(),
                    sort_keys=True,
                    cls=stripe.StripeObjectEncoder
                )
            )
            if data["id"] == stripe_event["id"] and stripe_event["data"] == data["data"]:
                return data
            else:
                raise serializers.ValidationError({"error": _("Event is not valid")})
        else:
            raise serializers.ValidationError({"error": _("Event must contain id, type and livemode")})


class PaymentSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=app_settings.PLANS_CHOICES, required=True)
    token = serializers.CharField(required=True)


class EventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        fields = '__all__'
