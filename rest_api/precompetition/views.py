from django.http import Http404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from multidb_account.precompetition.models import PreCompetition
from .permissions import IsAuthenticatedAthleteOrConnectedCoach, IsPreCompetitionOwnerOrConnectedCoach
from .serializers import PreCompetitionCreateUpdateListSerializer


class PreCompetitionCreateList(APIView):
    """
    Create/List/Update pre competition assessments
    """

    permission_classes = (IsAuthenticatedAthleteOrConnectedCoach,)

    def get_queryset(self, uid):

        queryset = PreCompetition.objects.using(self.request.user.country).filter(athlete_id=uid).all()

        latest = self.request.query_params.get('latest', None)
        if latest is not None:
            queryset = queryset.order_by('-date_created')[:1]

        start_date = self.request.query_params.get('start_date', None)
        if start_date is not None:
            queryset = queryset.filter(date__gt=parse_date(start_date))

        end_date = self.request.query_params.get('end_date', None)
        if end_date is not None:
            queryset = queryset.filter(date__lt=parse_date(end_date))

        return queryset

    def get(self, request, uid):
        """
        List all athlete's pre competition assessments.
        """
        queryset = self.get_queryset(uid)
        serializer = PreCompetitionCreateUpdateListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, uid):
        """
        Create a new pre competition assessment.
        """
        serializer = PreCompetitionCreateUpdateListSerializer(data=request.data,
                                                              context={'uid': uid,
                                                                       'user': request.user,
                                                                       'country': request.user.country,
                                                                       'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PreCompetitionDetail(APIView):
    """
    Update pre competition assessment..
    """

    permission_classes = (IsPreCompetitionOwnerOrConnectedCoach,)

    def get_object(self, request, pcid):
        try:
            pre_competition = PreCompetition.objects.using(request.user.country).get(pk=pcid)
            self.check_object_permissions(request, pre_competition)
            return pre_competition
        except PreCompetition.DoesNotExist:
            raise Http404

    def get(self, request, uid, pcid):
        """
        List pre competition assessment details.
        """
        pre_competition = self.get_object(request, pcid)
        serializer = PreCompetitionCreateUpdateListSerializer(pre_competition)
        return Response(serializer.data)

    def put(self, request, uid, pcid):
        """
        Update pre competition assessment details.
        """
        pre_competition = self.get_object(request, pcid)
        serializer = PreCompetitionCreateUpdateListSerializer(pre_competition, data=request.data,
                                                              context={'uid': uid,
                                                                       'request': request,
                                                                       'country': request.user.country,
                                                                       'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


