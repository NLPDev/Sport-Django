from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from payment_gateway.models import Customer
from rest_api.permissions import IsValidDisableCustomersToken


class AwsHealth(APIView):
    """
    An endpoint for aws to check health.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        """
        An endpoint for aws to check health.
        """
        return Response(status=status.HTTP_200_OK)


class DisableExpiredCustomers(APIView):
    permission_classes = (AllowAny, IsValidDisableCustomersToken)

    def post(self, request):
        """
        An endpoint for disabling expired customers.
        """
        Customer.disable_expired()
        return Response(status=status.HTTP_200_OK)
