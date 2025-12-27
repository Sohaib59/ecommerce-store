from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import UserProfile
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    ChangePasswordSerializer,
)


class UserRegistrationViewSet(viewsets.ViewSet):
    """
    Viewset for user registration.
    Allows new users to create an account.
    """
    permission_classes = [AllowAny]

    def create(self, request):
        """
        Register a new user.
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'User registered successfully'
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class UserLoginViewSet(viewsets.ViewSet):
    """
    Viewset for user login.
    Authenticates users and provides authentication token.
    """
    permission_classes = [AllowAny]

    def create(self, request):
        """
        Login user and return authentication token.
        """
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': 'Login successful'
                },
                status=status.HTTP_200_OK
            )
        return Response(
            serializer.errors,
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserViewSet(viewsets.ModelViewSet):
    """
    Viewset for user management.
    - List: Returns all users (Admin only)
    - Retrieve: Get user details
    - Update: Update user information
    - Delete: Delete user account (Admin only)
    - me: Get current user details
    - change_password: Change user password
    - logout: Logout user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Admin users can see all users, regular users can only see themselves.
        """
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'list']:
            permission_classes = [IsAdminUser]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated]
        elif self.action == 'destroy':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current authenticated user details.
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change password for the current user.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response(
                    {'message': 'Password changed successfully'},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'old_password': ['Wrong password.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user by deleting their authentication token.
        """
        try:
            request.user.auth_token.delete()
            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user account (Admin only).
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(
            {'message': f'User {user.username} has been deactivated'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        """
        Activate a user account (Admin only).
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(
            {'message': f'User {user.username} has been activated'},
            status=status.HTTP_200_OK
        )


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Viewset for user profile management.
    - List: Returns all profiles (Admin only)
    - Retrieve: Get profile details
    - Update: Update profile information
    - Delete: Delete profile (Admin only)
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Admin users can see all profiles, regular users can only see their own.
        """
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)

    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['list', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['retrieve', 'update', 'partial_update', 'create']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        Create a new user profile for the current user.
        """
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """
        Update user profile.
        """
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_profile(self, request):
        """
        Get the current user's profile.
        """
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """
    Standalone logout endpoint.
    Deletes the user's authentication token.
    """
    try:
        request.user.auth_token.delete()
        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Standalone user registration endpoint.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'User registered successfully'
            },
            status=status.HTTP_201_CREATED
        )
    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Standalone user login endpoint.
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Login successful'
            },
            status=status.HTTP_200_OK
        )
    return Response(
        serializer.errors,
        status=status.HTTP_401_UNAUTHORIZED
    )
