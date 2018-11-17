from rest_framework import permissions


class IsAchievementOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an achievement to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # check if user is creator of the obj
        return obj.created_by == request.user
