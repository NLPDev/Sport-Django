from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsAuthenticatedAndHasOwnAssessmentPermission(permissions.BasePermission):
    """
    Custom permissions to update own assessed assessment permissions.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user) and request.user.id == int(view.kwargs.get('uid'))


class IsAuthenticatedAndConnected(permissions.BasePermission):
    """
    Custom permissions to access assessed assessments
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user) and \
               (request.user.id == int(view.kwargs.get('uid')) or request.user.is_connected_to(view.kwargs.get('uid')))


class IsTeamMember(permissions.BasePermission):
    """
    Custom permission to only allow team members.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user)

    def has_object_permission(self, request, view, team):
        # check if user is a team member
        return team.athletes.filter(pk=request.user.id).exists() \
               or team.coaches.filter(pk=request.user.id).exists() \
               or request.user.id == team.owner.id \
               or (team.organisation and team.organisation.login_users.filter(id=request.user.id).exists())
