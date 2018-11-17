from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsCoachTeamMember(permissions.BasePermission):
    """
    Custom permission to only allow coach team members.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user)

    def has_object_permission(self, request, view, team):
        # check if user is a team member
        return team.coaches.filter(pk=request.user.id).exists() \
               or request.user.id == team.owner.id \
               or (team.organisation and team.organisation.login_users.filter(id=request.user.id).exists())


class IsAuthenticatedCoachOrOrganisation(permissions.BasePermission):
    """
    Custom permissions to access assessed assessments
    """

    def has_permission(self, request, view):
        if not is_authenticated(request.user):
            return False
        return request.user.is_coach() or request.user.is_organisation()


class IsTeamMemberOrOwner(permissions.BasePermission):
    """
    Custom permission to only allow owner of a Team to edit, members to list.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user)

    def has_object_permission(self, request, view, team):
        # check if user is a team member or team's owner for listing
        if request.method == 'GET':
            return team.athletes.filter(pk=request.user.id).exists() \
                   or team.coaches.filter(pk=request.user.id).exists() \
                   or request.user.id == team.owner.id \
                   or (team.organisation and team.organisation.login_users.filter(pk=request.user.id).exists())
        # check if user is the team's owner for update
        if request.method == 'PUT':
            return request.user.id == team.owner.id
        return False


class IsTeamOwner(permissions.BasePermission):
    """
    Custom permission to only allow owner of a Team to edit, members to list.
    """

    def has_permission(self, request, view):
        return is_authenticated(request.user)

    def has_object_permission(self, request, view, team):
        # check if user is a team member or team's owner for listing
        return request.user.id == team.owner.id
