SECRET_KEY = "test-secret-key-not-for-production"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "taggit",
    "wagtail.users",
    "wagtail.images",
    "wagtail.search",
    "wagtail.documents",
    "wagtail.admin",
    "wagtail",
    "tests.testapp",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

WAGTAIL_SITE_NAME = "Test"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
