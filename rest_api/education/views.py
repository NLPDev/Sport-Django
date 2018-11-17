from rest_framework.viewsets import ModelViewSet

from .permissions import IsEducationOwner
from .serializers import EducationSerializer
from multidb_account.education.models import Education


class EducationViewSet(ModelViewSet):
    """
    A viewset for viewing and editing user achievements.
    """
    permission_classes = (IsEducationOwner,)
    serializer_class = EducationSerializer
    lookup_url_kwarg = 'eid'

    def get_queryset(self):
        return Education.objects.using(self.request.user.country).filter(user=self.kwargs['uid'])
