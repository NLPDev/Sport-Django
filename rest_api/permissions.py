from django.conf import settings as django_settings
from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsOwnerOrDeny(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        # check if user is owner
        return obj.id == request.user.id


class IsValidDisableCustomersToken(permissions.BasePermission):
    """
    Custom permission to only allow requests with a valid request.data['token'].
    """

    def has_permission(self, request, view):
        return request.data.get('token') == django_settings.DISABLE_EXPIRED_CUSTOMERS_TOKEN


class IsAuthenticatedAthlete(permissions.BasePermission):
    """
    Custom permissions to only allow requests from athletes
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user) and request.user.is_athlete()
