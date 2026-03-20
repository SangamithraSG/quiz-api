"""
permissions.py (users app)

Custom permission classes.

In DRF, a permission class has one job: given a request and a view,
return True (allow) or False (deny).

We attach these to views using:
  permission_classes = [IsAdminUser]
"""

from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Only allows access to users whose role is 'admin'.
    Regular users are denied even if they are authenticated.
    """

    message = "You must be an admin to perform this action."

    def has_permission(self, request, view):
        # request.user is the currently logged-in user (from JWT token)
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_user
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission.
    Allows access if the user owns the object OR is an admin.

    Used for things like: "can this user view/edit this quiz attempt?"
    The view must call self.get_object() which triggers has_object_permission().
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        # Must be logged in first
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admins can access anything
        if request.user.is_admin_user:
            return True

        # Otherwise, check if the object belongs to this user.
        # Objects can have a 'user' field OR a 'created_by' field — handle both.
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user
        return False
