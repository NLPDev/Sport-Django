from rest_framework import permissions
from rest_framework.compat import is_authenticated


class AllowAnyCreateOrIsAuthenticated(permissions.BasePermission):
    """
    Custom permission to only allow write for any, read for authenticated request.
    """

    def has_permission(self, request, view):
        return request.method == 'POST' or (request.user and is_authenticated(request.user))

