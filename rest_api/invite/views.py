from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from multidb_account.constants import INVITE_PENDING
from rest_api.mixins import UserInviteSaltMixin

from multidb_account.invite.models import Invite
from multidb_account.team.models import Team

from .serializers import UserInviteRevokeSerializer, UserInviteSerializer, UserInviteConfirmSerializer, \
    UserPendingInviteListSerializer, UserInviteResendSerializer, UserInviteUnlinkSerializer

UserModel = get_user_model()


class UserInvite(UserInviteSaltMixin, APIView):
    """
    An endpoint to send user invite to connect.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UserInviteSerializer(
            data=request.data,
            context={'request': request, 'salt': self.salt},
            many=isinstance(request.data, list),
        )
        serializer.is_valid(raise_exception=False)
        if not serializer.validated_data:
            if hasattr(serializer, 'child') and serializer.child.custom_validated_data:
                serializer._validated_data = serializer.child.custom_validated_data
            else:
                raise ValidationError(serializer.errors)

        serializer.save()

        response_data = {
            'detail': _('User invite e-mails have been sent.'),
            'errors': serializer.errors,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class UserInviteResend(UserInviteSaltMixin, APIView):
    """
    An endpoint to resend user invite.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UserInviteResendSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": _("User invite e-mails have been resent.")}, status=status.HTTP_200_OK)


class UserPendingInviteList(UserInviteSaltMixin, APIView):
    """
    An endpoint to list user's invites (sent to him or created by him).
    """
    permission_classes = (IsAuthenticated,)

    def get_object(self, request, pk):
        try:
            user = UserModel.objects.using(request.user.country).get(pk=pk)

            # Call to check permissions first
            self.check_object_permissions(self.request, user)
            return user

        except UserModel.DoesNotExist:
            raise Http404

    def get_queryset(self):
        return Invite.objects.using(self.request.user.country).all()

    def get(self, request, uid):
        user = self.get_object(request, uid)

        # Fetch all pending invites for the current user
        filters = Q(requester=user)
        filters = filters & Q(status=INVITE_PENDING)
        invites = self.get_queryset().filter(filters).order_by('date_sent')

        serializer = UserPendingInviteListSerializer(invites, many=True, context={'request': request})
        return Response(serializer.data)


class TeamPendingInviteList(UserInviteSaltMixin, APIView):
    """
    An endpoint to list team's invites.
    """
    permission_classes = (IsAuthenticated,)

    def get_object(self, request, pk):
        try:
            team = Team.objects.using(request.user.country).get(pk=pk)

            # Call to check permissions first
            self.check_object_permissions(self.request, team)
            return team

        except Team.DoesNotExist:
            raise Http404

    def get_queryset(self):
        return Invite.objects.using(self.request.user.country).all()

    def get(self, request, tid):
        team = self.get_object(request, tid)

        # Fetch all pending invites for the current team
        invites = self.get_queryset().filter(team=team, status=INVITE_PENDING).order_by('date_sent')

        serializer = UserPendingInviteListSerializer(invites, many=True, context={'request': request})
        return Response(serializer.data)


class UserInviteConfirm(UserInviteSaltMixin, APIView):
    """
    An endpoint for to set new user's password.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = UserInviteConfirmSerializer(data=request.data,
                                                 context={
                                                     'salt': self.salt,
                                                     'request': request
                                                 })

        serializer.is_valid(raise_exception=True)
        requester = serializer.save()
        return Response(requester, status=status.HTTP_200_OK)


class UserInviteUnlink(UserInviteSaltMixin, DestroyAPIView):
    """
    An endpoint to unlink connected user by specifying `linked_user` (user email).
    """
    permission_classes = (IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        serializer = UserInviteUnlinkSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        # perform delete in save()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserInviteRevoke(UserInviteSaltMixin, DestroyAPIView):
    """
    An endpoint to cancel specific invitation by specifying either its `id` or `user_invite_token`.
    """
    permission_classes = (IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        ctx = {'user': request.user, 'salt': self.salt, 'request': request, 'recipient_is_current_user': False}
        serializer = UserInviteRevokeSerializer(
            data=request.data,
            context=ctx,
            many=isinstance(request.data, list),
        )

        serializer.is_valid(raise_exception=True)
        # perform delete in save()
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
