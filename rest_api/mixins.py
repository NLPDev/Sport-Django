from django.conf import settings as django_settings
from django.contrib.auth import hashers
from django.core import signing
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from multidb_account.constants import INVITE_CANCELED, INVITE_PENDING, USER_INVITE_SALT
from multidb_account.invite.models import Invite
from multidb_account.multidb_auth_backend import UserModel


class PasswordSaltMixin(object):
    salt = 'password_reset'


class UserInviteSaltMixin(object):
    salt = USER_INVITE_SALT



class PasswordSaltMixin(object):
    salt = 'password_reset'


class UserInviteSaltMixin(object):
    salt = USER_INVITE_SALT

class PasswordSaltMixin(object):
    salt = 'password_reset'


class UserInviteSaltMixin(object):
    salt = USER_INVITE_SALT
class PasswordSaltMixin(object):
    salt = 'password_reset'


class UserInviteSaltMixin(object):
    salt = USER_INVITE_SALT
class PasswordSaltMixin(object):
    salt = 'password_reset'


class UserInviteSaltMixin(object):
    salt = USER_INVITE_SALT

class ValidateInviteTokenMixin(serializers.Serializer):
    """
    Mixin to provide `validate_user_invite_token` method that checks invitation token and sets common attrs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.invite = self.invites = self.localized_db = self.requester = self.recipient = None

    def validate_user_invite_token(self, token):
        try:
            connection_args = signing.loads(
                token,
                max_age=getattr(django_settings, 'USER_INVITE_TOKEN_EXPIRES'),
                salt=self.context['salt']
            )
        except signing.BadSignature:
            raise serializers.ValidationError(_('User connection token is not valid.'))

        self.localized_db = connection_args.get('localized_db')

        # Fetch last invite for this token from history and validate if it exists
        token_hash = hashers.make_password(token, salt=self.context['salt'])

        self.invite = Invite.objects.using(self.localized_db) \
            .filter(invite_token_hash=token_hash).order_by('pk').last()

        if self.invite is not None:

            # Keep track of validated invites in order to have access to them from the parent ListSerializer
            self.invites = self.invites or []
            self.invites.append(self.invite)

            if self.invite.date_sent <= Invite.objects.expire_date:
                raise serializers.ValidationError(
                    {'token': _('The invite is expired.')})

            elif self.invite.status == INVITE_CANCELED:
                raise serializers.ValidationError({'token': _(
                    'This invite has been cancelled, please '
                    're-invite the necessary e-mail address to connect.'
                )})

            elif self.invite.status != INVITE_PENDING:
                raise serializers.ValidationError({'token': _('The invite is not in pending status.')})

        else:
            raise serializers.ValidationError(
                {'token': _('There are no invites for the token provided')})

        self.requester = self.invite.requester

        # Fetch recipient obj
        if self.context.get('recipient_is_current_user', True):
            self.recipient = self.context['request'].user
        else:
            try:
                self.recipient = UserModel.objects.using(self.localized_db).get(email=self.invite.recipient)
            except UserModel.DoesNotExist:
                raise serializers.ValidationError(
                    {"error": _("Unknown recipient email: {}".format(self.invite.recipient))})

        if self.recipient.email.lower() != self.invite.recipient.lower():
            raise serializers.ValidationError(
                {'token': _(
                    'Please, login with the same email to which invite was sent.')})

        return token

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
