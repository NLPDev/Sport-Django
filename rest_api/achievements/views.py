from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from multidb_account.achievements.models import Achievement, Badge
from .permissions import IsAchievementOwner
from .serializers import AchievementSerializer, BadgeSerializer


class AchievementViewSet(ModelViewSet):
    """
    A viewset for viewing and editing user achievements.
    """

    permission_classes = (IsAuthenticated, IsAchievementOwner,)
    serializer_class = AchievementSerializer
    lookup_url_kwarg = 'aid'

    def get_queryset(self):
        return Achievement.objects.using(self.request.user.country).filter(created_by=self.kwargs['uid'])


class BadgeViewSet(ReadOnlyModelViewSet):
    """
    A viewset for viewing and editing user badges.
    """

    serializer_class = BadgeSerializer
    queryset = Badge.objects.all()
    lookup_url_kwarg = 'bid'
