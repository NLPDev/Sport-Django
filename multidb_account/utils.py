from django.conf import settings
from django.contrib.auth import get_user_model


def get_user_from_localized_databases(username, localized_db=None):
    """
    This function get a user object from localized databases.
    :param username:
    :param localized_db:
    :return user:
    """
    debug = getattr(settings, 'DEBUG', False)

    localized_databases = [localized_db] if localized_db else getattr(settings, 'DATABASES', None)
    UserModel = get_user_model()
    user = None

    for database in localized_databases:
        try:
            filters = {'{}__{}'.format(UserModel.USERNAME_FIELD, 'iexact'): username}
            user = UserModel.objects.using(database).get(**filters)

        except UserModel.DoesNotExist:
            if debug:
                print("DEBUG: multidb_auth_backend -- User NOT found in database: " + database)
            user = None
        if user:
            if debug:
                print("DEBUG: multidb_auth_backend -- User found in database: " + database)
            break

    if user:
        return user


def get_localized_database(username):
    '''
    This function get the localized database name based on the user's email address.
    :param username:
    :return user:
    '''
    debug = getattr(settings, 'DEBUG', False)
    localized_databases = getattr(settings, 'LOCALIZED_DATABASES', None)
    UserModel = get_user_model()
    for database in localized_databases:
        try:
            user = UserModel.objects.using(database).get(**{UserModel.USERNAME_FIELD: username})
        except UserModel.DoesNotExist:
            if debug:
                print("DEBUG: multidb_auth_backend -- User NOT found in database: " + database)
            user = None
        if user:
            if debug:
                print("DEBUG: multidb_auth_backend -- User found in database: " + database)
            break

    if user:
        return user.country
    else:
        return None


def dictfetchall(cursor):
    """ Return all rows from a cursor as a dict """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]