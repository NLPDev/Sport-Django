from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, ListAPIView, DestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from multidb_account.sport.models import Sport
from .serializers import SportSerializer, ChosenSportSerializer
from rest_api.permissions import IsOwnerOrDeny

UserModel = get_user_model()


class SportList(ListCreateAPIView):
    """
    List all sports available, or create a new sport.
    """

    serializer_class = SportSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Sport.objects.using(self.request.user.country).filter(is_available=True)

    def get(self, request, format=None):
        """
        List all sports available.
        """
        queryset = self.get_queryset()
        serializer = SportSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        """
        Create a new sport.
        """
        serializer = SportSerializer(data=request.data, context={'country': request.user.country})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChosenSport(APIView):
    """
    List sports chosen by user or add a sport to a user.
    """

    serializer_class = ChosenSportSerializer
    permission_classes = (IsOwnerOrDeny,)

    def get_object(self, request, uid):
        try:
            user = UserModel.objects.using(request.user.country).get(pk=uid)
            self.check_object_permissions(self.request, user)
            return user
        except ObjectDoesNotExist:
            raise Http404

    def get_queryset(self):
        return self.request.user.chosensport_set.all()

    def get(self, request, uid, format=None):
        """
        List sports chosen by user.
        """
        # Call to check permissions first
        self.get_object(request, uid)
        queryset = self.get_queryset()
        serializer = ChosenSportSerializer(queryset, many=True)
        return Response(serializer.data)

    def put(self, request, uid, format=None):
        """
        Update user sports.
        """
        # Here no single instance is passed but a list of instances through request.data. For now 'put' doesn't support
        # multiple updates at the same time. Passing no instance means the serializer "create" method will
        # be called instead of the 'update'. The update logic lies in the serializer "create" for now
        #  TODO: this has to be improved in the futur

        valid_data = []
        rejected_data = []
        error_found = False
        for chosen_sport in request.data:
            validation_serializer = ChosenSportSerializer(data=chosen_sport, context={'country': request.user.country,
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
            serializer = ChosenSportSerializer(data=valid_data, many=isinstance(valid_data, list),
                                               context={'country': request.user.country, 'user': request.user})
            if serializer.is_valid():
                serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

