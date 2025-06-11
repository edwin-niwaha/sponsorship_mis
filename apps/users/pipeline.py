import logging

logger = logging.getLogger(__name__)

# def create_profile(backend, user, response, *args, **kwargs):
#     """Ensure the user has a profile, assigning a default role only if it's not already set."""
#     logger.info(f"Running create_profile for user: {user}")

#     profile, created = Profile.objects.get_or_create(user=user)

#     if created:
#         logger.info(f"Profile created for user: {user}")

#     uid = kwargs.get("uid", None)
#     logger.info(f"UID from social auth: {uid}")

#     # Assign a default role only if it does not exist
#     if not profile.role or profile.role.strip() == "":
#         profile.role = "guest"
#         profile.save()
#         logger.info(f"Profile updated with role 'guest' for user: {user}")
#     else:
#         logger.info(f"Profile role already set ({profile.role}), no update needed.")
