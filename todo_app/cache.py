from django.core.cache import cache

CACHE_PREFIX = "task_list"
CACHE_TIMEOUT = 60 * 5  # 5 minutes
VERSION_KEY_PREFIX = "task_list_version"


def task_list_cache_key(request, *args, **kwargs):
    """
    Custom cache key function for task list endpoint.
    Includes prefix and dynamic version based on user's task changes.
    """
    user_id = request.user.id
    version = get_user_cache_version(user_id)
    return f"{CACHE_PREFIX}:v{version}:user_{user_id}"


def get_user_cache_version(user_id):
    """Get the current cache version for a user."""
    version_key = f"{VERSION_KEY_PREFIX}:user_{user_id}"
    version = cache.get(version_key)

    if version is None:
        version = 1
        cache.set(version_key, version, timeout=None)  # Never expire version keys

    return version


def increment_user_cache_version(user_id):
    """Increment the cache version for a user, invalidating old cached data."""
    version_key = f"{VERSION_KEY_PREFIX}:user_{user_id}"
    version = cache.get(version_key, 0)
    new_version = version + 1
    cache.set(version_key, new_version, timeout=None)  # Never expire version keys
    return new_version
