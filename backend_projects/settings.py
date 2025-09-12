import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-0-sntg)ni=u26o+9=)dafe87265r&t49(uwose90eh52cr!z1%"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "0") == "1"

ALLOWED_HOSTS = ["*"]

CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
ASGI_APPLICATION = "backend_projects.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.environ.get("REDIS_HOST", "127.0.0.1"),
                    int(os.environ.get("REDIS_PORT", "6379")),
                )
            ],
            "symmetric_encryption_keys": [SECRET_KEY],
        },
    },
}

# Application definition
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django.contrib.gis",  # Required for GeoDjango
    "channels",
    "corsheaders",  # CORS support
    "rest_framework",
    "rest_framework.authtoken",
    "shared.apps.SharedConfig",
    "auth_app.apps.AuthAppConfig",
    "blogs_app.apps.BlogsAppConfig",
    "expense_tracker_app.apps.ExpenseTrackerAppConfig",
    "todo_app.apps.TodoAppConfig",
    "weather_app.apps.WeatherAppConfig",
    "note_markdown_app.apps.NoteMarkdownAppConfig",
    "url_shortner_app.apps.UrlShortnerAppConfig",
    "device_classifier.apps.DeviceClassifierConfig",
    "map_app.apps.MapAppConfig",
    "chat_app.apps.ChatAppConfig",
    "ai_chat.apps.AiChatConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware - must be first
    "shared.middleware.LoggingMiddleware",  # Make sure this is second
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all origins in development

CORS_ALLOWED_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

ROOT_URLCONF = "backend_projects.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend_projects.wsgi.application"
ASGI_APPLICATION = "backend_projects.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",  # Use PostGIS backend
        "NAME": os.environ.get("DB_NAME", "backend_projects"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "backend_projects.renderer.CustomJSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",  # Add standard token auth
        "auth_app.authentication.BearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

# Additional static files directories (if any)
STATICFILES_DIRS = [
    BASE_DIR / "docs",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INTERNAL_IPS = [
    "127.0.0.1",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# LLM Server Configuration
LLM_SERVER_CONFIG = {
    "BASE_URL": os.environ.get("LLM_SERVER_URL", "http://localhost:8001"),
    "DEFAULT_MODEL": os.environ.get("LLM_DEFAULT_MODEL", "qwen3:8b"),
    "TIMEOUT": int(
        os.environ.get("LLM_TIMEOUT", "120")
    ),  # Increased for geospatial tool processing
    "MAX_TOKENS": int(os.environ.get("LLM_MAX_TOKENS", "2000")),
    "TEMPERATURE": float(os.environ.get("LLM_TEMPERATURE", "0.7")),
    "ENABLE_TOOLS": os.environ.get("LLM_ENABLE_TOOLS", "true").lower() == "true",
}

# Update logging settings
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
}
