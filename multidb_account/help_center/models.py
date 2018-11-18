from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import models
from django.template import loader
from django.utils.translation import ugettext_lazy as _


class HelpCenterReport(models.Model):
    organization = models.CharField(verbose_name=_('organization'), max_length=255)
    coach_name = models.CharField(verbose_name=_('coach name'), max_length=255)
    date = models.DateField(verbose_name=_('date'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('date created'), blank=True)
    details = models.TextField(verbose_name=_('details'))
    name = models.CharField(verbose_name=_('name'), max_length=255, blank=True)
    owner = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Help Center Report'
        verbose_name_plural = 'Help Center Reports'

    def send_notification_emails(self):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'obj': self,
        }

        msg_plain = loader.render_to_string(django_settings.HELP_CENTER_NOTIFICATION_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.HELP_CENTER_NOTIFICATION_EMAIL_TEMPLATE + '.html', context)
        subject = _('New Help Center Reports notification')

        send_mail(subject,
                  msg_plain,
                  django_settings.DEFAULT_FROM_EMAIL,
                  django_settings.HELP_CENTER_FORM_EMAILS,
                  html_message=msg_html)


class OrganisationSupport(models.Model):
    organisation = models.ForeignKey('multidb_account.Organisation', verbose_name=_('organisation'),
                                     related_name='support')
    name = models.CharField(verbose_name=_('name'), max_length=255)
    email = models.EmailField(verbose_name=_('email address'), max_length=255)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_('Phone number must be 9 to 15 digits entered in the format "+999999999" where "+" is optional'))
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    support_type = models.CharField(verbose_name=_('support type'), max_length=255)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('date created'))
    details = models.TextField(verbose_name=_('details'))
    owner = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Organisation Support'
        verbose_name_plural = 'Organisation Support'

    def send_notification_emails(self):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'obj': self,
        }

        msg_plain = loader.render_to_string(
            django_settings.HELP_CENTER_ORG_SUPPORT_NOTIFICATION_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(
            django_settings.HELP_CENTER_ORG_SUPPORT_NOTIFICATION_EMAIL_TEMPLATE + '.html', context)
        subject = _('New Organisation Support notification')

        send_mail(subject,
                  msg_plain,
                  django_settings.DEFAULT_FROM_EMAIL,
                  django_settings.HELP_CENTER_FORM_EMAILS,
                  html_message=msg_html)
