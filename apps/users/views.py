"""
views.py (users app)

Views handle HTTP requests and return HTTP responses.
Each class = one URL endpoint (or a group of related ones).

Flow: URL → View → Serializer → Model → Database
"""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsAdminUser
from .serializers import RegisterSerializer, UserPublicSerializer, UserProfileSerializer


# ── Authentication ────────────────────────────────────────────────────────────

class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Accepts: { "username": "...", "password": "..." }
    Returns: { "access": "<jwt>", "refresh": "<jwt>" }

    The access token goes in the Authorization header:
      Authorization: Bearer <access_token>

    We inherit from TokenObtainPairView which does all the heavy lifting.
    """
    permission_classes = [AllowAny]  # Anyone can try to log in


class RegisterView(generics.CreateAPIView):
    """
    POST /api/users/register/

    Creates a new user account.
    Returns the user data (without password) on success.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # Anyone can register

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)   # Validates and raises 400 if invalid
        user = serializer.save()

        # Return user data using the public serializer (no password)
        return Response(
            {
                "message": "Account created successfully.",
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Profile ───────────────────────────────────────────────────────────────────

class MyProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/  → View your own profile
    PUT  /api/users/me/  → Update your profile (email, bio)
    PATCH /api/users/me/ → Partial update (just one field)

    Only works for the logged-in user (uses request.user).
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Instead of getting a user by ID from URL, we return the logged-in user
        return self.request.user


# ── Admin: User Management ─────────────────────────────────────────────────────

class UserListView(generics.ListAPIView):
    """
    GET /api/users/  → List all users (admin only)

    Returns a paginated list of all users.
    Regular users cannot access this.
    """
    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [IsAdminUser]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/users/<id>/  → View any user's profile (admin only)
    PUT    /api/users/<id>/  → Update any user (admin only)
    DELETE /api/users/<id>/  → Delete a user (admin only)
    """
    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        # Safety: prevent admin from deleting themselves
        if user == request.user:
            return Response(
                {"error": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.delete()
        return Response(
            {"message": f"User '{user.username}' deleted."},
            status=status.HTTP_200_OK,
        )


class PromoteUserView(APIView):
    """
    POST /api/users/<id>/promote/

    Promotes a regular user to admin role.
    Only existing admins can do this.

    Body: { "role": "admin" } or { "role": "user" }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get("role")
        if new_role not in [User.ROLE_USER, User.ROLE_ADMIN]:
            return Response(
                {"error": "Invalid role. Choose 'user' or 'admin'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = new_role
        user.save()

        return Response(
            {"message": f"User '{user.username}' is now '{new_role}'."},
            status=status.HTTP_200_OK,
        )
