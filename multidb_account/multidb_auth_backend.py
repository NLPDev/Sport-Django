from django.contrib.auth import get_user_model

from .middleware import thread_locals
from .utils import get_user_from_localized_databases

# get the custom user model.
UserModel = get_user_model()


class MultidbAuthBackend(object):
    """
    This custom auth backend is used to authenticate users against multiple databases.
    Active databases are defined in settings.LOCALIZED_DATABASES.
    """

    def __init__(self):
        self.auth_database = 'default'

    def authenticate(self, request, email=None, password=None):
        # localized_db = getattr(thread_locals, 'admin_show_localized_db', None)
        # user = get_user_from_localized_databases(email, localized_db)
        user = get_user_from_localized_databases(email)

        if user:
            self.auth_database = user.country
            request.session['localized_db'] = user.country

            if user.check_password(password):
                return user
            else:
                return None

    def get_user(self, user_id):
        try:
            localized_db = getattr(thread_locals, 'localized_db', self.auth_database)

            return UserModel.objects.using(localized_db).get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
