from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from .models import Profile


def role_required(role):
    def decorator(function):
        def check_role(user):
            if user.is_authenticated:
                try:
                    profile = user.profile
                    return profile.role == role
                except Profile.DoesNotExist:
                    return False
            return False

        return user_passes_test(check_role, login_url="login")(function)

    return decorator


manager_required = role_required("manager")
staff_required = role_required("staff")
administrator_required = role_required("administrator")
