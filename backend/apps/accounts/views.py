"""
Session-cookie authentication endpoints.

Flow for a browser/SPA client:
  1. GET  /api/v1/auth/csrf/      -> sets the `csrftoken` cookie
  2. POST /api/v1/auth/login/     -> header `X-CSRFToken: <cookie value>`; sets HttpOnly `sessionid`
  3. Subsequent unsafe requests send `X-CSRFToken`; the browser sends cookies automatically.
"""
from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    """Issue the CSRF cookie the SPA needs before its first unsafe request."""

    permission_classes = [AllowAny]

    @extend_schema(responses={204: None})
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnforceCsrfMixin:
    """
    DRF exempts APIViews from Django's CSRF middleware and only re-checks CSRF for
    already-authenticated sessions. Login/register are anonymous, so we enforce it
    explicitly (prevents login-CSRF). Failures surface as a JSON 403.
    """

    def initial(self, request: Request, *args, **kwargs) -> None:
        SessionAuthentication().enforce_csrf(request)
        super().initial(request, *args, **kwargs)  # type: ignore[misc]


class RegisterView(EnforceCsrfMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(EnforceCsrfMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)  # rotates the session key (session-fixation protection)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        logout(request)  # flushes the server-side session
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)
