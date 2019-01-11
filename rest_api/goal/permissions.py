from django.contrib.auth import get_user_model
from rest_framework import permissions

UserModel = get_user_model()


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of object to view/edit it.
    """
    def has_object_permission(self, request, view, obj):
        # check if user is owner of the obj
        return obj.user == request.user


class AreUsersConnected(permissions.BasePermission):
    """
    Custom permission to only allow connected users to see each other goals.
    """
    def has_permission(self, request, view):
        try:
            target_user = UserModel.objects.using(request.user.country).get(pk=view.kwargs['uid'])
        except Exception:
            return False
        return request.user in {u.user for u in target_user.get_linked_users()}









class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of object to view/edit it.
    """
    def has_object_permission(self, request, view, obj):
        # check if user is owner of the obj
        return obj.user == request.user


class AreUsersConnected(permissions.BasePermission):
    """
    Custom permission to only allow connected users to see each other goals.
    """
    def has_permission(self, request, view):
        try:
            target_user = UserModel.objects.using(request.user.country).get(pk=view.kwargs['uid'])
        except Exception:
            return False
        return request.user in {u.user for u in target_user.get_linked_users()}
