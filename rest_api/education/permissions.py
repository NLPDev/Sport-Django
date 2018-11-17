from rest_framework import permissions


class IsEducationOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an education to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # check if user is owner of the obj
        return request.method in permissions.SAFE_METHODS or obj.user == request.user
