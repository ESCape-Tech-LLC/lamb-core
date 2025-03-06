import os

settings_config = os.environ.get("LAMB_SETTINGS_CONFIG", "django")

if settings_config == "django":
    from django.conf import settings
else:
    from .pydantic_settings import settings
