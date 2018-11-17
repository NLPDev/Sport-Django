from rest_framework.mixins import RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from multidb_account.promocode.models import Promocode
from rest_api.permissions import IsAuthenticatedAthlete
from .serializers import PromocodeSerializer


class PromocodeViewSet(RetrieveModelMixin, GenericViewSet):
    """
    A viewset for viewing (validating) promocodes.
    """
    permission_classes = (IsAuthenticatedAthlete,)
    serializer_class = PromocodeSerializer
    lookup_field = 'code'

    def get_queryset(self):
        return Promocode.objects.using(self.request.user.country)
