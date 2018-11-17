from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from multidb_account.assessment.models import Assessed, AssessmentTopCategory, ChosenAssessment, AssessmentSubCategory
from multidb_account.assessment_tree import get_assessment_tree_filtered_by_org_own_assessments
from multidb_account.team.models import Team
from multidb_account.user.models import Organisation
from rest_api.team.permissions import IsCoachTeamMember
from .permissions import IsAuthenticatedAndConnected, IsAuthenticatedAndHasOwnAssessmentPermission, IsTeamMember
from .serializers import AssessmentsTreeListSerializer, \
    ChosenAssessmentCreateSerializer, ChosenAssessmentTreeListSerializer, \
    ChosenAssessmentListSerializer, AssessmentTopCategoryPermissionUpdateSerializer, \
    AssessmentTopCategoryPermissionListSerializer, ChosenAssessmentUpdateSerializer, \
    TeamChosenAssessmentListSerializer, AssessedListSerializer

UserModel = get_user_model()


class AssessmentList(ListAPIView):
    """
    List all assessments available in PSR.
    """

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = AssessmentTopCategory.objects.using(self.request.user.country).all().order_by('id')

        top_category_ids = self.request.query_params.get('top_category_ids', None)
        if top_category_ids is not None:
            top_category_ids = [int(x) for x in top_category_ids.split(',')]
            qs = qs.filter(pk__in=top_category_ids)

        return self._filter_by_own_assessments_only_organisations(qs)

    def _filter_by_own_assessments_only_organisations(self, qs):
        """
        If the user belongs to an Organisation with `.own_assessments_only = True`,
        filter the QuerySet by `Organisation.own_assessments`
        """
        user = self.request.user

        private_org_ids, our_org_ids = self._get_org_ids()
        tree = get_assessment_tree_filtered_by_org_own_assessments(user.country, private_org_ids, our_org_ids)

        top_ass_ids = {x['topcat_id'] for x in tree}
        qs = qs.filter(id__in=top_ass_ids)
        qs._cached_tree = tree
        return qs

    def _get_org_ids(self):
        """ Get list of user's orgs """
        user = self.request.user

        direct_membership_qs = user.member_of_organisations.using(user.country)
        direct_membership_ids = {org.id for org in direct_membership_qs}
        if user.is_organisation():
            direct_membership_ids.add(user.organisation.id)
        direct_membership_own_assessments_only_ids = {
            org.id
            for org in Organisation.objects.using(user.country)
            .filter(own_assessments_only=True, id__in=direct_membership_ids)
        }

        if hasattr(user.typeduser, 'team_membership'):
            team_membership_qs = user.typeduser.team_membership.using(user.country).filter(organisation__isnull=False)
            team_membership_ids = {team.organisation.id for team in team_membership_qs}
            team_membership_own_assessments_only_ids = {
                team.organisation.id
                for team in team_membership_qs.filter(organisation__own_assessments_only=True)
            }
        else:
            team_membership_ids = team_membership_own_assessments_only_ids = set()

        return (
            direct_membership_own_assessments_only_ids | team_membership_own_assessments_only_ids,
            direct_membership_ids | team_membership_ids,
        )

    def get(self, request, format=None):
        """ List the whole nested assessments structure """
        user_from_own_assessments_only_org = request.user.member_of_organisations.filter(own_assessments_only=True).exists() or (
                hasattr(request.user.typeduser, 'team_membership')
                and request.user.typeduser.team_membership.filter(organisation__own_assessments_only=True).exists()
        )
        qs = self.get_queryset()
        tree = qs._cached_tree
        subcat_ids = {x['subcat_id'] for x in tree}
        extra_subcat_ids = AssessmentSubCategory.objects.using(request.user.country).filter(id__in=subcat_ids)
        subcat_ids.update({x.parent_sub_category_id for x in extra_subcat_ids})
        ctx = {
            'request': request,
            'user_from_own_assessments_only_org': user_from_own_assessments_only_org,
            'subcat_ids': subcat_ids,
        }
        serializer = AssessmentsTreeListSerializer(qs, many=True, context=ctx)
        return Response(serializer.data)


class ChosenAssessmentListUpdateCreate(APIView):
    """
    Add one or multiple assessment(s) to an assessed.
    List assessed's assessments.
    """

    permission_classes = (IsAuthenticatedAndConnected,)

    def get_queryset(self):
        assessed = Assessed.objects.using(self.request.user.country).filter(id=self.kwargs['uid']).last()
        if assessed is None:
            return ChosenAssessment.objects.none()
        queryset = assessed.chosenassessment_set.all().order_by('id')

        id = self.request.query_params.get('id', None)
        if id is not None:
            queryset = queryset.filter(id=id)

        team_id = self.request.query_params.get('team_id', None)
        if team_id is not None:
            queryset = queryset.filter(team_id=team_id)

        assessment_id = self.request.query_params.get('assessment_id', None)
        if assessment_id is not None:
            queryset = queryset.filter(assessment_id=assessment_id)

        assessor_id = self.request.query_params.get('assessor_id', None)
        if assessor_id is not None:
            queryset = queryset.filter(assessor_id=assessor_id)

        start_date = self.request.query_params.get('start_date', None)
        if start_date is not None:
            queryset = queryset.filter(date_assessed__gt=parse_date(start_date))

        end_date = self.request.query_params.get('end_date', None)
        if end_date is not None:
            queryset = queryset.filter(date_assessed__lt=parse_date(end_date))

        return queryset

    def get_top_categories(self):
        top_categories = AssessmentTopCategory.objects.using(self.request.user.country).all().order_by('id')

        top_category_ids = self.request.query_params.get('top_category_ids', None)
        if top_category_ids is not None:
            top_category_ids = [int(x) for x in top_category_ids.split(',')]
            top_categories = top_categories.filter(pk__in=top_category_ids)
        return top_categories

    def get(self, request, uid, format=None):
        """
        List user's assessments.
        """
        queryset = self.get_queryset()

        rendering = self.request.query_params.get('rendering', None)
        if rendering == "flat":
            return Response(ChosenAssessmentListSerializer(queryset, many=True,
                                                           context={'assessed_id': uid,
                                                                    'country': request.user.country,
                                                                    'user': request.user}).data)
        if rendering == "tree" or rendering is None:
            top_categories = self.get_top_categories()
            return Response(ChosenAssessmentTreeListSerializer(top_categories, many=True,
                                                               context={'queryset': queryset}).data)

    def post(self, request, uid):
        """
        Create user's assessments.
        """
        valid_data = []
        rejected_data = []
        error_found = False
        dry_run = request.data and request.data[0].get('dry_run', False)

        context = {
            'assessed_id': uid,
            'team_id': None,
            'country': request.user.country,
            'user': request.user,
            'dry_run': dry_run,
        }

        for assessment in request.data:
            # Provide team_id = None as it is an assessment made in direct (not through team)
            validation_serializer = ChosenAssessmentCreateSerializer(data=assessment, context=context)

            if validation_serializer.is_valid():
                valid_data.append(validation_serializer.data)
            else:
                item = {}
                item.update(validation_serializer.data)
                for key in validation_serializer.errors.keys():
                    val = validation_serializer.errors.get(key)
                item.update({"error": " ".join(str(x) for x in val)})
                rejected_data.append(item)
                error_found = True

        response_data = {"valid": valid_data, "rejected": rejected_data}

        if error_found:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        serializer = ChosenAssessmentCreateSerializer(data=valid_data,
                                                      many=isinstance(valid_data, list),
                                                      context=context)
        if serializer.is_valid(raise_exception=True):
            if not dry_run:
                serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, uid, format=None):
        """
        Update user's assessments.
        """
        # Here no single instance is passed but a list of instances through request.data. For now 'put' doesn't support
        # multiple updates at the same time. Passing no instance means the serializer "create" method will
        # be called instead of the 'update'. The update logic lies in the serializer "create" for now
        #  TODO: this has to be improved in the futur

        valid_data = []
        rejected_data = []
        error_found = False
        for assessment in request.data:
            validation_serializer = ChosenAssessmentUpdateSerializer(data=assessment,
                                                                     context={'assessed_id': uid,
                                                                              'country': request.user.country,
                                                                              'user': request.user})
            if validation_serializer.is_valid():
                valid_data.append(validation_serializer.data)
            else:
                item = {}
                item.update(validation_serializer.data)
                for key in validation_serializer.errors.keys():
                    val = validation_serializer.errors.get(key)
                item.update({"error": " ".join(str(x) for x in val)})
                rejected_data.append(item)
                error_found = True

        response_data = {"valid": valid_data, "rejected": rejected_data}

        if error_found:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = ChosenAssessmentUpdateSerializer(data=valid_data, many=isinstance(valid_data, list),
                                                          context={'assessed_id': uid,
                                                                   'country': request.user.country,
                                                                   'user': request.user})
            if serializer.is_valid():
                serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)


class TeamAssessmentsAverage(APIView):
    """ List team assessments average values per team """

    permission_classes = (IsCoachTeamMember,)

    def get_queryset(self):
        return ChosenAssessment.objects.using(self.request.user.country) \
            .filter(team_id=self.kwargs['tid']) \
            .order_by('id')

    def get_top_categories(self):
        return AssessmentTopCategory.objects.using(self.request.user.country).all().order_by('id')

    def get(self, request, tid, format=None):
        top_categories = self.get_top_categories()
        ctx = {
            'queryset': self.get_queryset(),
            'get_averages': True,
        }
        return Response(ChosenAssessmentTreeListSerializer(top_categories, many=True, context=ctx).data)


class AssessmentTopCategoryPermission(APIView):
    """
    Update/List assessed's assessment permissions
    """

    permission_classes = (IsAuthenticatedAndHasOwnAssessmentPermission,)

    def get_queryset(self):
        assessed = self.request.user.get_assessed()
        queryset = assessed.assessmenttopcategorypermission_set.all().order_by('id')

        top_category_ids = self.request.query_params.get('top_category_ids', None)
        if top_category_ids is not None:
            top_category_ids = [int(x) for x in top_category_ids.split(',')]
            queryset = queryset.filter(assessment_top_category_id__in=top_category_ids)

        assessor_id = self.request.query_params.get('assessor_id', None)
        if assessor_id is not None:
            queryset = queryset.filter(assessor_id=assessor_id)

        assessor_has_access = self.request.query_params.get('assessor_has_access', None)
        if assessor_has_access is not None:
            queryset = queryset.filter(assessor_has_access=assessor_has_access)

        return queryset

    def get(self, request, uid, format=None):
        """
        List assessed's assessment permission.
        """
        queryset = self.get_queryset()
        return Response(AssessmentTopCategoryPermissionListSerializer(queryset, many=True).data)

    def put(self, request, uid, format=None):
        """
        Update assessed's assessment permissions.
        """
        # Here no single instance is passed through request.data but a list of instances. For now 'put' doesn't support
        # multiple updates at the same time. Passing no single instance means the serializer "create" method will
        # be called instead of the 'update'. The update logic lies in the serializer "create" for now
        #  TODO: this has to be improved in the futur

        serializer = AssessmentTopCategoryPermissionUpdateSerializer(data=request.data,
                                                                     many=isinstance(request.data, list),
                                                                     context={'assessed_id': uid,
                                                                              'country': request.user.country,
                                                                              'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------


class TeamChosenAssessmentListUpdateCreate(APIView):
    """
    Create/List/Update team members assessments at once
    """

    permission_classes = (IsTeamMember,)

    def get_object(self, request, tid):
        try:
            team = Team.objects.using(request.user.country).get(pk=tid)
            self.check_object_permissions(self.request, team)
            return team
        except Team.DoesNotExist:
            raise Http404

    def get_queryset(self, team):
        team_members_data = []

        for member in team.athletes.all().order_by('user_id'):

            queryset = member.assessed.chosenassessment_set.filter(team_id=team.id)

            assessor_id = self.request.query_params.get('assessor_id', None)
            if assessor_id is not None:
                queryset = queryset.filter(assessor_id=assessor_id)

            assessment_id = self.request.query_params.get('assessment_id', None)
            if assessment_id is not None:
                queryset = queryset.filter(assessment_id=assessment_id)

            latest = self.request.query_params.get('latest', None)
            if latest is not None:
                queryset = queryset.order_by('-date_assessed')[:1]

            start_date = self.request.query_params.get('start_date', None)
            if start_date is not None:
                queryset = queryset.filter(date_assessed__gt=parse_date(start_date))

            end_date = self.request.query_params.get('end_date', None)
            if end_date is not None:
                queryset = queryset.filter(date_assessed__lt=parse_date(end_date))

            if queryset:
                team_members_data += queryset[:]
            else:
                team_members_data.append(member.assessed)

        return team_members_data

    def get(self, request, tid):
        """
        List team members assessments.
        """
        team = self.get_object(request, tid)
        team_members_data = self.get_queryset(team)
        assessments = []

        for item in team_members_data:
            if isinstance(item, ChosenAssessment):
                assessments.append(TeamChosenAssessmentListSerializer(item, context={'request': request}).data)
            if isinstance(item, Assessed):
                assessments.append({"value": None,
                                    "assessment_id": self.request.query_params.get('assessment_id', None),
                                    "assessed": AssessedListSerializer(item, context={'request': request}).data})
        return Response(assessments)

    def post(self, request, tid):
        """
        Create team members assessments.
        """
        valid_data = []
        rejected_data = []
        error_found = False

        for assessment in request.data:
            # Provide assessed_id = None as it is an assessment made through a team
            validation_serializer = ChosenAssessmentCreateSerializer(data=assessment,
                                                                     context={'team_id': tid,
                                                                              'assessed_id': None,
                                                                              'country': request.user.country,
                                                                              'user': request.user})

            if validation_serializer.is_valid():
                valid_data.append(validation_serializer.data)
            else:
                item = {}
                item.update(validation_serializer.data)
                for key in validation_serializer.errors.keys():
                    val = validation_serializer.errors.get(key)
                item.update({"error": " ".join(str(x) for x in val)})
                rejected_data.append(item)
                error_found = True

        response_data = {"valid": valid_data, "rejected": rejected_data}

        if error_found:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = ChosenAssessmentCreateSerializer(data=valid_data, many=isinstance(valid_data, list),
                                                          context={'team_id': tid,
                                                                   'assessed_id': None,
                                                                   'country': request.user.country,
                                                                   'user': request.user})
            if serializer.is_valid():
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
