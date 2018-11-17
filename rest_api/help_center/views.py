from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from multidb_account.help_center.models import HelpCenterReport, OrganisationSupport
from .permissions import IsOrganisationMember
from .serializers import HelpCenterReportSerializer, OrganisationSupportSerializer


class HelpCenterReportViewSet(CreateModelMixin, GenericViewSet):
    """
    A viewset for creating help center reports.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = HelpCenterReportSerializer

    def get_queryset(self):
        return HelpCenterReport.objects.using(self.request.user.country).select_related('owner')

    def perform_create(self, serializer):
        obj = serializer.save()
        obj.send_notification_emails()


class OrganisationSupportViewSet(CreateModelMixin, GenericViewSet):
    """
    A viewset for creating organisation support tickets.
    """
    permission_classes = [IsOrganisationMember]
    serializer_class = OrganisationSupportSerializer

    def get_queryset(self):
        return OrganisationSupport.objects.using(self.request.user.country).select_related('owner')

    def perform_create(self, serializer):
        obj = serializer.save()
        obj.send_notification_emails()
