from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User

GRADUATION_YEAR_MIN = 1980
GRADUATION_YEAR_AHEAD = 6  # current students up to ~6 years before passing out


def graduation_year_range() -> tuple[int, int]:
    from django.utils import timezone

    return GRADUATION_YEAR_MIN, timezone.now().year + GRADUATION_YEAR_AHEAD


def check_college_name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise serializers.ValidationError("Enter your college name.", code="blank")
    return value


def check_graduation_year(value: int) -> int:
    low, high = graduation_year_range()
    if not low <= value <= high:
        raise serializers.ValidationError(f"Enter a year between {low} and {high}.", code="invalid_year")
    return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "college_name", "graduation_year", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    college_name = serializers.CharField(max_length=200)
    graduation_year = serializers.IntegerField()

    def validate_college_name(self, value: str) -> str:
        return check_college_name(value)

    def validate_graduation_year(self, value: int) -> int:
        return check_graduation_year(value)

    def validate_full_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.", code="blank")
        return value.strip()

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists.", code="email_taken"
            )
        return email

    def validate(self, attrs: dict) -> dict:
        # Run Django's password validators against an unsaved user so the
        # similarity validator can compare with name/email.
        candidate = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            college_name=validated_data["college_name"],
            graduation_year=validated_data["graduation_year"],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"].strip().lower(),
            password=attrs["password"],
        )
        if user is None:
            # Same message for unknown email and wrong password (no account enumeration).
            raise serializers.ValidationError(
                "Invalid email or password.", code="invalid_credentials"
            )
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "college_name", "graduation_year"]
        extra_kwargs = {"college_name": {"required": False}, "graduation_year": {"required": False}}

    def validate_college_name(self, value: str) -> str:
        return check_college_name(value)

    def validate_graduation_year(self, value):
        if value is None:
            raise serializers.ValidationError("Enter your year of passing out.", code="required")
        return check_graduation_year(value)

    def validate_full_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.", code="blank")
        return value.strip()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_current_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.", code="wrong_password")
        return value

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError(
                {"new_password": [serializers.ErrorDetail("Choose a different password.", code="password_unchanged")]}
            )
        try:
            password_validation.validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.", code="wrong_password")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate(self, attrs: dict) -> dict:
        from .password_reset import user_from_token

        user = user_from_token(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError(
                {"token": [serializers.ErrorDetail(
                    "This reset link is invalid or has expired. Request a new one.", code="invalid_token")]}
            )
        try:
            password_validation.validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        attrs["user"] = user
        return attrs
