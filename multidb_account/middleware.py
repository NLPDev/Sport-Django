import threading

from django.conf import settings

# A class that represents thread-local data.
from multidb_account.admin import get_localized_db_from_url

thread_locals = threading.local()


class MultiDbMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Inspect the request before it goes to the view. Check if the user is authenticated.
        - If the user is authenticated, it adds a 'db_localized' parameter to the request object. 
        This 'db_localized' parameter is based on the user's country and will be used to define which database
        to use.
        - Any other anonynmous request will be proceeded using the 'default' database. """

        debug = getattr(settings, 'DEBUG', False)

        if request.session.get('localized_db'):
            thread_locals.localized_db = request.session.get('localized_db')

        thread_locals.in_admin = request.path.startswith('/admin/')
        if thread_locals.in_admin:
            thread_locals.admin_show_localized_db = get_localized_db_from_url(request.path)

        if request.user.is_authenticated():
            request.localized_db = request.user.country

            if debug:
                print('DEBUG: Custom middleware -- User authenticated')
        else:
            if thread_locals.in_admin:
                request.localized_db = thread_locals.admin_show_localized_db
            else:
                request.localized_db = 'default'

            if debug:
                print('DEBUG: Custom middleware -- User NOT authenticated')
