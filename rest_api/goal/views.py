from django.contrib.auth import get_user_model
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import mixins

from multidb_account.goal.models import Goal
from .serializers import GoalSerializer
from .permissions import IsOwner, AreUsersConnected

UserModel = get_user_model()


class MyGoalViewSet(ModelViewSet):
    """
    A viewset for viewing and editing user own goals.
    """
    permission_classes = (IsOwner,)
    serializer_class = GoalSerializer

    def get_queryset(self):
        # A user sees only his own goals
        return Goal.objects.using(self.request.user.country).filter(user=self.request.user)


class UserGoalViewSet(mixins.ListModelMixin, GenericViewSet):
    """
    A viewset for viewing other user's goals.
    """
    permission_classes = (AreUsersConnected,)
    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.using(self.request.user.country).filter(user_id=self.kwargs['uid'])
