from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsOrganisationMember(permissions.BasePermission):

    def has_permission(self, request, view):
        # check if user is an organisation member
        if request.method == 'POST':
            return is_authenticated(request.user) and request.user.organisation
        return False
