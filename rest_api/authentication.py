from django.utils.dateformat import format
from django.utils.translation import ugettext as _
from rest_framework import exceptions
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.settings import api_settings

from multidb_account.constants import USER_TYPE_ATHLETE
from multidb_account.utils import get_user_from_localized_databases

jwt_get_username_from_payload = api_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER
jwt_get_user_id_from_payload_handler = api_settings.JWT_PAYLOAD_GET_USER_ID_HANDLER


class PsrJSONWebTokenAuthentication(JSONWebTokenAuthentication):
    """ Expire token on password change and force user to re-authenticate. """

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        username = jwt_get_username_from_payload(payload)
        payload_user_id = jwt_get_user_id_from_payload_handler(payload)

        if not username:
            msg = _('Invalid payload.')
            raise exceptions.AuthenticationFailed(msg)

        user = get_user_from_localized_databases(username)
        if not user:
            msg = _('Invalid signature.')
            raise exceptions.AuthenticationFailed(msg)

        if user.id != payload_user_id:
            msg = _('Invalid signature.')
            raise exceptions.AuthenticationFailed(msg)

        # Only for Athlete users who have a customer model extension
        if user.user_type == USER_TYPE_ATHLETE and hasattr(user.athleteuser, 'customer'):
            if user.athleteuser.customer.payment_status == 'locked_out':
                msg = _('User account has been locked out.')
                raise exceptions.AuthenticationFailed(msg)

        if not user.is_active:
            msg = _('User account is disabled.')
            raise exceptions.AuthenticationFailed(msg)

        orig_iat = int(payload['orig_iat'])
        jwt_last_expired = int(format(user.jwt_last_expired, 'U'))

        if orig_iat < jwt_last_expired:
            msg = 'Users must re-authenticate after logging out.'
            raise exceptions.AuthenticationFailed(msg)

        return user
