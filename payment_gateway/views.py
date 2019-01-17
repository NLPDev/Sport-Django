from django.conf import settings as django_settings
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import stripe

from .models import Customer
from .parsers import CustomJSONParser
from .webhooks import webhook_event_handler
from .serializers import *
from .permissions import IsOwnerOrDenyPayment


class StripeView(APIView):
    """ Generic API StripeView """
    permission_classes = (IsOwnerOrDenyPayment,)

    def get_customer(self):
        try:
            return Customer.objects.using(self.request.user.country). \
                get(athlete_id=self.request.user.athleteuser.customer.athlete_id)
        except Customer.DoesNotExist:
            return None

    def get_or_create_customer(self, user):
        customer = self.get_customer()

        if not customer.get_stripe_id():
            customer.create_stripe_customer(user)

        had_card = customer.has_card()
        return customer, had_card


class PaymentView(StripeView):
    """ See, set the customer payment details """

    def post(self, request, *args, **kwargs):
        del args, kwargs

        try:
            serializer = PaymentSerializer(data=request.data)
            if serializer.is_valid():

                # Get psr customer object
                customer, had_card = self.get_or_create_customer(request.user)

                token = serializer.validated_data.get('token')
                customer.add_replace_card(token)

                if not customer.has_card():
                    return Response({'error': _("Customer has no card set")}, status=status.HTTP_400_BAD_REQUEST)

                plan = serializer.validated_data.get('plan', None)
                customer.add_update_plan(plan)
                customer.post_add_update_plan(had_card)

                return Response(serializer.validated_data, status=status.HTTP_200_OK)

            # Athletes that signed up with a 100% discount promocode
            elif serializer.data.get('token') is None and serializer.data.get('plan') == 'not_needed':

                # Get psr customer object
                customer, had_card = self.get_or_create_customer(request.user)
                customer.post_add_update_plan(had_card, payment_status='not_needed')

                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except stripe.CardError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.RateLimitError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.InvalidRequestError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.AuthenticationError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.APIConnectionError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.StripeError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionView(StripeView):
    """ See, change/set the customer subscription plan """

    def get(self, request, *args, **kwargs):
        customer = self.get_customer()
        if not customer.get_stripe_id() or not customer.get_plan():
            return Response({'error': _("Customer has no active payment account")}, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = SubscriptionSerializer({'plan': customer.get_plan()})
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        try:
            serializer = SubscriptionSerializer(data=request.data)

            if serializer.is_valid():
                plan = serializer.validated_data.get('plan', None)
                customer = self.get_customer()
                if customer.has_card():
                    subscription = customer.add_update_plan(plan)
                    return Response(serializer.validated_data, status=status.HTTP_200_OK)
                else:
                    return Response({'error': _("Customer has no card set")}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except stripe.CardError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.RateLimitError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.InvalidRequestError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.AuthenticationError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.APIConnectionError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.StripeError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)




class CardView(StripeView):
    """ List/Add/Update customer card details """

    def get(self, request, *args, **kwargs):
        customer = self.get_customer()
        if not customer.get_stripe_id() or not customer.has_card():
            return Response({'error': _("Customer has no active card")}, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = CardSerializer(customer.get_card())
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        try:
            serializer = CardTokenSerializer(data=request.data)

            if serializer.is_valid():
                # Get psr customer object
                customer = self.get_customer()
                if not customer.get_stripe_id():
                    customer.create_stripe_customer(request.user)
                token = serializer.validated_data.get('token')
                customer.add_replace_card(token)

                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except stripe.CardError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.RateLimitError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.InvalidRequestError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.AuthenticationError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.APIConnectionError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.StripeError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)


class WebhookView(StripeView):
    permission_classes = (AllowAny,)
    parser_classes = (CustomJSONParser,)

    stripe_webhook_secret = django_settings.STRIPE_WEBHOOK_SECRET

    def post(self, request):

        try:
            # Verify Stripe signature
            raw_body = request.data.pop('raw_body')
            payload = raw_body.decode()
            sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', None)
            event = stripe.Webhook.construct_event(payload, sig_header, self.stripe_webhook_secret)

        except ValueError as e:
            # Invalid payload
            return Response({"error": _("Invalid payload")}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response({"error": _("Invalid stripe webhook signature")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer = WebhookSerializer(data=event)

            if serializer.is_valid():
                validated_event = webhook_event_handler(serializer.validated_data)
                if validated_event:
                    event_serializer = EventSerializer(validated_event)
                    return Response(event_serializer.data['stripe_id'], status=status.HTTP_200_OK)
                else:
                    return Response({"warning": _("Customer not found. Event not recorded")},
                                    status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except stripe.CardError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.RateLimitError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.InvalidRequestError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.AuthenticationError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.APIConnectionError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except stripe.StripeError as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            error_data = {'error': smart_str(e) or _("Unknown error")}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
