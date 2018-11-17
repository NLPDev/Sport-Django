from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.parsers import MultiPartParser
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from multidb_account.constants import USER_TYPE_ATHLETE
from multidb_account.note.models import AthleteNote, CoachNote, File, ReturnToPlayType
from .permissions import IsOwnerOrReadOnly
from .serializers import FileSerializer, AthleteNoteSerializer, CoachNoteSerializer, ReturnToPlayTypeSerializer

UserModel = get_user_model()


class FileViewSet(ModelViewSet):
    """
    A viewset for viewing and editing files.
    """
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = FileSerializer
    parser_classes = (MultiPartParser,)

    def get_queryset(self):
        return File.objects.using(self.request.user.country).all()


class AthleteNoteViewSet(ModelViewSet):
    """
    A viewset for viewing and editing athlete notes.
    """
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = AthleteNoteSerializer
    lookup_url_kwarg = 'nid'

    def get_queryset(self):
        user = self.request.user
        filter_by_request_user = Q(owner_id=user.id)

        # Athletes only see their own notes
        if not user.is_athlete():
            filter_by_request_user = filter_by_request_user | Q(only_visible_to=user.id) | (Q(only_visible_to=None))

        qs = AthleteNote.objects.using(user.country) \
            .filter(filter_by_request_user)

        # Filter by owner-user
        uid = self.kwargs.get('uid')
        if uid is not None:
            qs = qs.filter(owner_id=uid)
        else:
            linked_athletes = user.get_linked_users()
            qs = qs.filter(owner__in=linked_athletes)
        return qs


class CoachNoteViewSet(ModelViewSet):
    """
    A viewset for viewing and editing coach notes.
    """
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = CoachNoteSerializer
    lookup_url_kwarg = 'nid'

    def get_queryset(self):
        user = self.request.user
        qs = CoachNote.objects.using(user.country)

        # Filter by owner-user
        uid = self.kwargs.get('uid')
        if uid is not None:
            qs = qs.filter(owner_id=uid)

        # Filter by athlete_id if requested by athlete user
        if user.user_type == USER_TYPE_ATHLETE:
            qs = qs.filter(
                Q(athlete_id=user.id) |
                Q(team__athletes=user.id)
            )

        # Filter by athlete_id query param
        athlete_id = self.request.query_params.get('athlete_id')
        if athlete_id is not None:
            qs = qs.filter(
                Q(athlete_id=athlete_id) |
                Q(team__athletes=athlete_id)
            )

        return qs


class ReturnToPlayTypeViewSet(ReadOnlyModelViewSet):
    """
    A viewset for viewing and editing return_to_play_types.
    """
    serializer_class = ReturnToPlayTypeSerializer

    def get_queryset(self):
        return ReturnToPlayType.objects.using(self.request.user.country).all()
