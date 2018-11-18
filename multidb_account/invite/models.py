from django.conf import settings as django_settings
from django.contrib.auth import hashers, get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import models
from django.template import loader
from django.utils.translation import ugettext_lazy as _

from multidb_account.choices import USER_TYPES, INVITE_STATUSES
from multidb_account.constants import USER_INVITE_SALT
from multidb_account.managers import InviteManager
from multidb_account.team.models import Team


UserModel = get_user_model()


class Invite(models.Model):
    requester = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name=_('requester'))
    team = models.ForeignKey(Team, blank=True, null=True, verbose_name=_('team'))
    invite_token_hash = models.CharField(max_length=255, verbose_name=_('token hash'))
    date_sent = models.DateTimeField(auto_now_add=True, verbose_name=_('date'))
    status = models.CharField(max_length=10, choices=INVITE_STATUSES, verbose_name=_('status'))
    recipient = models.EmailField(editable=True, verbose_name=_('recipient email'))
    recipient_type = models.CharField(verbose_name=_('recipient type'), choices=USER_TYPES, max_length=50, null=True)

    objects = InviteManager()

    @staticmethod
    def make_token(requester, recipient_email, recipient_type):
        token = signing.dumps({
            'requester_email': requester.email,
            'requester_type': requester.user_type,
            'localized_db': requester.country,
            'recipient_email': recipient_email,
            'recipient_type': recipient_type
        }, salt=USER_INVITE_SALT)

        token_hash = hashers.make_password(token, salt=USER_INVITE_SALT)

        return token, token_hash

    def send_email(self, token=None):
        resending = token is None
        if resending:
            token, token_hash = Invite.make_token(self.requester, self.recipient, self.recipient_type)

            # Update the invite.token_hash
            self.invite_token_hash = token_hash
            self.save(update_fields=('invite_token_hash',))

        name_pattern = '%s %s/' if self.requester.is_organisation() else '%s/%s'
        requester_name = name_pattern % (self.requester.first_name, self.requester.last_name)
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'user_invite_path': django_settings.PSR_APP_USER_INVITE_PATH,
            'image_name': "{}-to-{}.jpg".format(self.requester.user_type, self.recipient_type),
            'requester': self.requester,
            'requester_name': requester_name,
            'recipient_email': self.recipient,
            'recipient_type': self.recipient_type,
            'token': token
            # 'secure': self.request.is_secure(),
        }

        msg_plain = loader.render_to_string(django_settings.USER_INVITE_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.USER_INVITE_EMAIL_TEMPLATE + '.html', context)

        subject = _("You've been invited to connect on Personal Sport Record")

        send_mail(
            subject,
            msg_plain,
            django_settings.DEFAULT_FROM_EMAIL,
            [self.recipient],
            html_message=msg_html
        )

    def get_recipient_full_name(self, country):
        user = UserModel.objects.using(country).filter(email=self.recipient).first()
        if user is None:
            return ''
        return ('%s %s' % (user.first_name or '', user.last_name or '')).strip()
