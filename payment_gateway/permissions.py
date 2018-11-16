from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsOwnerOrDenyPayment(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_permission(self, request, view):
        if is_authenticated(request.user) and view.kwargs.get('uid'):
            # Check if authenticated user can access the view
            return int(view.kwargs.get('uid')) == request.user.athleteuser.customer.athlete_id
        else:
            return False

