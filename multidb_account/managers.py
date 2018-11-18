from datetime import timedelta

from django.conf import settings as django_settings
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone

from .constants import INVITE_PENDING
from .utils import get_user_from_localized_databases


class CustomUserManager(BaseUserManager):
    """Custom user manager for CustomUser."""

    def create_user(self, email, country, password=None, is_active=True):
        if not email:
            raise ValueError('User\'s email address must be set')
        if not country:
            raise ValueError('User\'s country must be set')
        user = self.model(
            email=self.normalize_email(email),
            country=country,
            is_active=is_active,
        )
        user.set_password(password)
        # Save performed against the localized database
        user.save(using=country)
        return user

    def create_superuser(self, email, country, password):
        user = self.create_user(
            email,
            password=password,
            country=country,
        )
        user.is_admin = True
        user.save(using=country)
        return user

    # We had to override the get_by_natural_key() to be able to look up
    # localized databases.
    def get_by_natural_key(self, username):
        return get_user_from_localized_databases(username)


class InviteManager(models.Manager):
    @property
    def expire_date(self):
        """
        Date in the past that marks all invites that were created before as expired.
        """

        return timezone.now() - timedelta(seconds=django_settings.USER_INVITE_TOKEN_EXPIRES)

    @property
    def timeout_date(self):
        """
        Date in the past that marks all invites that were created after as (too) recent.
        """

        return timezone.now() - timedelta(seconds=django_settings.USER_INVITE_TIMEOUT)

    def pending_nonexpired(self):
        return self.filter(date_sent__gt=self.expire_date, status=INVITE_PENDING)

    def recent(self):
        return self.filter(date_sent__gt=self.timeout_date)

    def delete_expired(self):
        return self.filter(date_sent__lte=self.expire_date).delete()
