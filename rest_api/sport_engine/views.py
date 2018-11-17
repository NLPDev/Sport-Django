from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from rest_api.team.serializers import TeamSerializer
from sport_engine.models import SportEngineEvent, SportEngineGame
from .serializers import SportEngineEventSerializer, SportEngineGameSerializer


class SportEngineBaseViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Validate team_id
        team_ser = TeamSerializer(data=self.request.query_params, context={'request': self.request})
        team_ser.is_valid(raise_exception=True)


class SportEngineEventViewSet(SportEngineBaseViewSet):
    serializer_class = SportEngineEventSerializer
    model = SportEngineEvent

    def get_queryset(self):
        super().get_queryset()

        # Filter queryset
        user = self.request.user
        return self.model.objects \
            .using(user.country) \
            .filter(Q(sport_engine_team__team__athletes__pk=user.pk) |
                    Q(sport_engine_team__team__coaches__pk=user.pk) |
                    Q(sport_engine_team__team__owner__pk=user.pk))


class SportEngineGameViewSet(SportEngineBaseViewSet):
    serializer_class = SportEngineGameSerializer
    model = SportEngineGame

    def get_queryset(self):
        super().get_queryset()

        # Filter queryset
        user = self.request.user
        return self.model.objects \
            .using(user.country) \
            .filter(Q(sport_engine_teams__team__athletes__pk=user.pk) |
                    Q(sport_engine_teams__team__coaches__pk=user.pk) |
                    Q(sport_engine_teams__team__owner__pk=user.pk))
