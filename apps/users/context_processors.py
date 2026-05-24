from apps.inventory.products.models import Product
from apps.sponsor.models import SponsorFeedback
from apps.users.models import Contact, Profile


def guest_profiles_context(request):
    return {
        "guest_profiles": Profile.objects.none(),
        "guest_count": 0,
    }


def guest_user_feedback_context(request):
    sponsor_feedback = SponsorFeedback.objects.unread().with_related()[:5]
    sponsor_feedback_count = SponsorFeedback.objects.unread().count()
    return {
        "user_feedback": Contact.objects.none(),
        "feedback_count": sponsor_feedback_count,
        "sponsor_feedback": sponsor_feedback,
        "sponsor_feedback_count": sponsor_feedback_count,
    }


def low_stock_alerts_context(request):
    return {
        "low_stock_products": Product.objects.none(),
        "low_stock_count": 0,
    }
