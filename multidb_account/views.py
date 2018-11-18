from django.conf import settings as django_settings
from django.core import signing
from django.views.generic import TemplateView

from .user.models import BaseCustomUser
from .constants import USER_TYPE_ATHLETE, USER_CONFIRM_ACCOUNT_SALT
from .utils import get_user_from_localized_databases


class ResetPasswordEmailTemplate(TemplateView):
    template_name = django_settings.RESET_PASSWORD_EMAIL_TEMPLATE + '.html'

    def get_context_data(self, **kwargs):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'user': get_user_from_localized_databases('athlete10@ca.ca'),
            'reset_password_path': django_settings.PSR_APP_RESET_PASSWORD_PATH,
            'token': 'ImN5cmlsLm1pZ25vdGV0QGdtYWlsLmNvbSI:1dGSgJ:ekLDf82QREoLvqYha2xz9vIf8eo0',
        }
        return context


class ResetPasswordConfirmEmailTemplate(TemplateView):
    template_name = django_settings.RESET_PASSWORD_CONFIRM_EMAIL_TEMPLATE + '.html'

    def get_context_data(self, **kwargs):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user': get_user_from_localized_databases('athlete10@ca.ca'),
        }
        return context


class UserInviteEmailTemplate(TemplateView):
    template_name = django_settings.USER_INVITE_EMAIL_TEMPLATE + '.html'

    def get_context_data(self, **kwargs):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user_invite_path': django_settings.PSR_APP_USER_INVITE_PATH,
            'image_name': 'coach' + "-to-" + 'athlete' + ".jpg",
            'requester': get_user_from_localized_databases('coach10@ca.ca'),
            'recipient_email': get_user_from_localized_databases('athlete10@ca.ca').email,
            'recipient_type': USER_TYPE_ATHLETE,
            'token': 'ImN5cmlsLm1pZ25vdGV0QGdtYWlsLmNvbSI:1dGSgJ:ekLDf82QREoLvqYha2xz9vIf8eo0'
            # 'secure': self.request.is_secure(),
        }
        return context


class WelcomeEmailTemplate(TemplateView):
    template_name = django_settings.WELCOME_EMAIL_TEMPLATE + '.html'

    def get_context_data(self, **kwargs):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user': get_user_from_localized_databases('athlete10@ca.ca'),
        }
        return context


class ConfirmAccountConfirmTemplate(TemplateView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None

    def get_template_names(self, **kwargs):
        if self.user.is_staff:
            return [django_settings.CONFIRM_ACCOUNT_CONFIRM_TEMPLATE + '.html']
        return [django_settings.WELCOME_EMAIL_TEMPLATE + '.html']

    def get_context_data(self, **kwargs):
        self.user = self.process_token_and_get_user(kwargs['token'])

        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user': self.user,
        }
        return context

    @staticmethod
    def process_token_and_get_user(token):

        # Get user data from token
        user_id = user = localized_db = None
        try:
            data = signing.loads(token, salt=USER_CONFIRM_ACCOUNT_SALT)
            user_id = data['user_id']
            localized_db = data['localized_db']
        except signing.BadSignature:
            pass

        # Get user obj
        if user_id and localized_db:
            try:
                user = BaseCustomUser.objects.using(localized_db).get(pk=user_id)
            except BaseCustomUser.DoesNotExist:
                pass

            if user and not user.is_active:
                user.is_active = True
                user.save(update_fields=('is_active',))

        return user
