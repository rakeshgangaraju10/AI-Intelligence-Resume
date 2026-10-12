from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

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
