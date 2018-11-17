from rest_framework import permissions
from rest_framework.compat import is_authenticated


class IsAuthenticatedAthleteOrConnectedCoach(permissions.BasePermission):
    """
    Custom permission to only allow athlete to create and athlete/owner and connected coach to list.
    """

    def has_permission(self, request, view):
        # check if user athlete owner or connected coach
        if request.method == 'GET':
            return is_authenticated(request.user) and \
                   (request.user.id == int(view.kwargs.get('uid')) or
                    request.user.is_connected_to(view.kwargs.get('uid')))
        # check if user is an authenticated athlete
        if request.method == 'POST':
            return is_authenticated(request.user) and request.user.is_athlete() and \
                   request.user.id == int(view.kwargs.get('uid'))
        return False


class IsPreCompetitionOwnerOrConnectedCoach(permissions.BasePermission):
    """
    Custom permission to only allow athlete/owner to update and connected coach to list.
    """

    def has_permission(self, request, view):
        if request.method == 'GET':
            return is_authenticated(request.user) and \
                   (request.user.id == int(view.kwargs.get('uid')) or
                    request.user.is_connected_to(view.kwargs.get('uid')))
        if request.method == 'PUT':
            return is_authenticated(request.user) and request.user.id == int(view.kwargs.get('uid'))
        return False

    def has_object_permission(self, request, view, pre_competition):
        # check if user is owner
        if request.method == 'GET':
            return True
        if request.method == 'PUT':
            return pre_competition.athlete.user_id == request.user.id

