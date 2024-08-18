from apps.users.models import Profile, Contact
from django.contrib.auth.decorators import login_required


def guest_profiles_context(request):
    # Fetch all profiles with the role "guest"
    guest_profiles = Profile.objects.filter(role="guest")

    # Calculate the number of guest profiles
    guest_count = guest_profiles.count()

    # Return context dictionary
    return {
        "guest_profiles": guest_profiles,
        "guest_count": guest_count,
    }


def guest_user_feedback_context(request):
    # Fetch all invalid feedback entries
    user_feedback = Contact.objects.filter(is_valid=False)

    # Calculate the count of invalid feedback entries
    feedback_count = user_feedback.count()

    # Return context dictionary
    return {
        "user_feedback": user_feedback,
        "feedback_count": feedback_count,
    }
