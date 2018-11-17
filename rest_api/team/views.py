from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import DestroyAPIView
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from multidb_account.team.models import Team
from .permissions import IsCoachTeamMember, IsAuthenticatedCoachOrOrganisation, IsTeamMemberOrOwner, IsTeamOwner
from .serializers import TeamPreCompetitionListSerializer, TeamListSerializer, TeamCreateSerializer,\
    TeamUpdateSerializer, TeamPictureUploadSerializer, TeamRevokeSerializer


class TeamPreCompetitionList(APIView):
    """
    List all athletes re competition assessments at once
    """

    permission_classes = (IsCoachTeamMember,)

    def get_object(self, request, tid):
        try:
            team = Team.objects.using(request.user.country).get(pk=tid)
            self.check_object_permissions(self.request, team)
            return team
        except Team.DoesNotExist:
            raise Http404

    def get_queryset(self, team):
        pre_comp = []

        for athlete in team.get_all_athletes():
            pre_comp.extend(athlete.precompetition_set.filter(team_id=team.id).order_by('-date')[:1])
        return pre_comp

    def get(self, request, tid):
        """
        List all athletes re competition assessments at once.
        """
        team = self.get_object(request, tid)
        pre_competitions = self.get_queryset(team)
        return Response(TeamPreCompetitionListSerializer(pre_competitions, many=True,
                                                         context={'request': request}).data)


class TeamCreateList(APIView):
    """
    List all teams available, or create a new team.
    """

    permission_classes = (IsAuthenticatedCoachOrOrganisation,)

    def get_queryset(self):
        return Team.objects.using(self.request.user.country).all()

    def get(self, request, format=None):
        """
        List all teams available.
        """
        queryset = self.get_queryset()
        serializer = TeamListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        """
        Create a new team.
        """
        serializer = TeamCreateSerializer(data=request.data, context={'country': request.user.country,
                                                                      "request": request,
                                                                      'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TeamDetail(APIView):
    """
    Retrieve, update or delete a team.
    """

    permission_classes = (IsTeamMemberOrOwner,)

    def get_object(self, request, tid):
        try:
            team = Team.objects.using(request.user.country).get(pk=tid)
            self.check_object_permissions(self.request, team)
            return team
        except Team.DoesNotExist:
            raise Http404

    def get(self, request, tid):
        """
        Retrieve team's details.
        """
        team = self.get_object(request, tid)
        serializer = TeamListSerializer(team, context={"request": request})
        return Response(serializer.data)

    def put(self, request, tid):
        """
        Update team's details.
        """
        team = self.get_object(request, tid)
        serializer = TeamUpdateSerializer(team, data=request.data, context={"request": request,
                                                                            'country': request.user.country,
                                                                            'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TeamPictureUpload(APIView):
    """
    Upload/Update team's picture.
    """
    permission_classes = (IsTeamOwner,)
    parser_classes = (FormParser, MultiPartParser,)

    def get_object(self, request, tid):
        try:
            team = Team.objects.using(request.user.country).get(pk=tid)
            self.check_object_permissions(self.request, team)
            return team
        except Team.DoesNotExist:
            raise Http404

    def put(self, request, tid, format=None):
        """
        Upload/Update team's picture.
        """
        team = self.get_object(request, tid)
        serializer = TeamPictureUploadSerializer(team, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeamRevoke(DestroyAPIView):
    """
    An endpoint to revoke team members.
    """
    permission_classes = (IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        serializer = TeamRevokeSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        # perform delete in save()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
