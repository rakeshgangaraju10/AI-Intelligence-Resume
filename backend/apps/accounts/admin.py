from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class UserAdminCreationForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name")


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    ordering = ["email"]
    list_display = ["email", "full_name", "college_name", "graduation_year", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active", "graduation_year"]
    search_fields = ["email", "full_name", "college_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "college_name", "graduation_year")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "usable_password", "password1", "password2"),
            },
        ),
    )
