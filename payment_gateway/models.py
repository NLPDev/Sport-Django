from datetime import timedelta
from django.conf import settings as django_settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from multidb_account.user.models import AthleteUser
from .settings import PLANS_CHOICES
from .choices import PAYMENT_STATUS
import stripe

from .signals import (
    cancelled,
    card_changed,
    subscription_made,
    webhook_processing_error,
    WEBHOOK_SIGNALS,
)


class StripeObject(models.Model):
    stripe_id = models.CharField(verbose_name=_('stripe id'), max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # pylint: disable=E0012,C1001
        abstract = True


class Customer(StripeObject):
    athlete = models.OneToOneField(AthleteUser, on_delete=models.CASCADE, primary_key=True)
    last_update = models.DateTimeField(default=timezone.now)
    payment_status = models.CharField(verbose_name=_('Payment status'), max_length=50,
                                      choices=PAYMENT_STATUS, default='no_card')
    last_payment_date = models.DateTimeField(verbose_name=_('Last payment date'), null=True, blank=True)
    grace_period_start = models.DateTimeField(verbose_name=_('Grace period start date'), null=True, blank=True)
    grace_period_end = models.DateTimeField(verbose_name=_('Grace period end date'), null=True, blank=True)

    def __unicode__(self):
        return self.athlete

    def __str__(self):
        return self.athlete.user.email

    #Auto update last_update
    def save(self, *args, **kwargs):
        self.last_update = timezone.now()
        super(Customer, self).save(*args, **kwargs)

    @receiver(WEBHOOK_SIGNALS["charge.succeeded"])
    def handle_charge_succeeded(instance, event_data, sender, **kwargs):
        instance.last_payment_date = timezone.now()
        instance.payment_status = 'up_to_date'
        instance.save()

    @receiver(WEBHOOK_SIGNALS["charge.failed"])
    def handle_charge_failed(instance, sender, event_data, **kwargs):
        instance.grace_period_start = timezone.now()
        instance.grace_period_end = timezone.now() + timedelta(days=30)
        instance.payment_status = 'grace_period'
        instance.save()

    @receiver(WEBHOOK_SIGNALS["customer.source.deleted"])
    def handle_source_deleted(instance, sender, event_data, **kwargs):
        instance.payment_status = 'no_card'
        instance.save()

    @receiver(WEBHOOK_SIGNALS["customer.subscription.deleted"])
    def handle_subscription_deleted(instance, sender, event_data, **kwargs):
        instance.payment_status = 'canceled'
        instance.save()
        instance.athlete.user.deactivate()

    def get_stripe_id(self):
        return self.stripe_id

    def get_last_payment_date(self):
        return self.last_payment_date

    def get_customer_payment_status(self):
        return self.payment_status

    def create_stripe_customer(self, user):
        # Create a new Stripe customer
        stripe_customer = stripe.Customer.create(
            email=user.email,
            description=user.first_name + ", " + user.last_name,
            # source='tok_visa_debit'
        )
        self.stripe_id = stripe_customer.id
        self.save()
        return stripe_customer

    def retrieve_stripe_customer(self):
        # Retrieve Stripe customer object
        if self.get_stripe_id():
            try:
                return stripe.Customer.retrieve(self.stripe_id)
            except:
                return None
        else:
            return None

    def _retrieve_stripe_subscription_by_id(self, sub_id):
        try:
            return stripe.Subscription.retrieve(sub_id)
        except:
            return None

    def _get_subscription_plan_name(self, sub):
        # Retrieve Stripe customer object
        try:
            return sub.data[0].plan.name
        except:
            return None

    def _get_subscription_plan_id(self, sub):
        # Retrieve Stripe customer object
        try:
            return sub.data[0].plan.id
        except:
            return None

    def get_plan(self):
        cus = self.retrieve_stripe_customer()
        try:
            return cus.subscriptions.data[0].plan.name
        except:
            return None

    def get_subscription_id(self):
        cus = self.retrieve_stripe_customer()
        return cus.subscriptions.data[0].id or None

    def add_update_plan(self, plan):
        current_plan = self.get_plan()
        if current_plan:
            subscription = self._retrieve_stripe_subscription_by_id(self.get_subscription_id())
            subscription.plan = PLANS_CHOICES.get(plan)
            subscription.save()
        else:
            subscription = stripe.Subscription.create(customer=self.get_stripe_id(), plan=PLANS_CHOICES.get(plan))
        return self._get_subscription_plan_name(subscription)

    def cancel_plan(self):
        current_plan = self.get_plan()
        if current_plan:
            subscription = self._retrieve_stripe_subscription_by_id(self.get_subscription_id())
            return subscription.delete()

    @classmethod
    def disable_expired(cls):
        for db in django_settings.DATABASES:
            cls.objects.using(db) \
                .filter(grace_period_end__lt=timezone.now()) \
                .exclude(payment_status='locked_out') \
                .update(payment_status='locked_out')

    def post_add_update_plan(self, had_card, payment_status='up_to_date'):
        if not had_card:
            self.athlete.user.send_welcome_email()

        self.payment_status = payment_status
        self.save(update_fields=['payment_status'])

# --------------------- card --------------------------

    def _retrieve_card(self, cus, card_id):
        try:
            return cus.sources.retrieve(card_id)
        except:
            return None

    def _retrieve_default_card(self, cus):
        try:
            return self._retrieve_card(cus, cus.default_source)
        except:
            return None

    def _push_create_card(self, cus, token):
        return cus.sources.create(source=token)

    def _push_delete_card(self, cus, card_id):
        return cus.sources.retrieve(card_id).delete()

    def has_card(self):
        cus = self.retrieve_stripe_customer()
        return True if self._retrieve_default_card(cus) else None

    def add_replace_card(self, token):
        cus = self.retrieve_stripe_customer()
        card = self._retrieve_default_card(cus)
        if card:
            self._push_delete_card(cus, card.id)
        return self._push_create_card(cus, token)

    def get_card(self):
        cus = self.retrieve_stripe_customer()
        card = self._retrieve_default_card(cus)
        if card:
            return card
        else:
            return None

    def delete_card(self):
        cus = self.retrieve_stripe_customer()
        card = self._retrieve_default_card(cus)
        if card:
            return self._push_delete_card(cus, card.id)
        else:
            return None

    def cancel(self):
        self.delete_card()
        self.cancel_plan()
        return True


class Event(StripeObject):
    customer = models.ForeignKey("Customer", null=True)
    type = models.CharField(verbose_name=_('stripe event type '), max_length=250, default="")
    livemode = models.BooleanField(verbose_name=_('stripe event livemode '), default=False)
    processed = models.BooleanField(verbose_name=_('stripe event processed status'), default=False)

    def __unicode__(self):
        return "%s - %s" % (self.type, self.stripe_id)


