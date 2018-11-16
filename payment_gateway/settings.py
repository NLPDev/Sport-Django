from django.conf import settings as django_settings
import stripe

stripe.api_key = django_settings.STRIPE_SECRET_KEY

PLANS_CHOICES = {
    "yearly": django_settings.STRIPE_YEARLY_PLAN_ID,
    "monthly": django_settings.STRIPE_MONTHLY_PLAN_ID,
    "yearly-full": django_settings.STRIPE_YEARLY_FULL_PLAN_ID,
    "monthly-full": django_settings.STRIPE_MONTHLY_FULL_PLAN_ID
}
