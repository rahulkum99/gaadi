from django.core.cache import cache

from fleet.constants import LIVE_SNAPSHOT_MINUTES, PLATFORM_DEFAULTS
from fleet.models import PlatformSettings

CACHE_KEY = "fleet:platform_settings"


def clear_platform_settings_cache():
    cache.delete(CACHE_KEY)


def get_platform_settings():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    settings, _ = PlatformSettings.objects.select_related("updated_by").get_or_create(
        singleton_key=1,
        defaults=PLATFORM_DEFAULTS,
    )
    cache.set(CACHE_KEY, settings, 30)
    return settings


def serialize_platform_settings(settings=None):
    settings = settings or get_platform_settings()
    updater = None
    if settings.updated_by_id:
        updater = settings.updated_by.full_name or settings.updated_by.email
    return {
        "daily_km_limit": settings.daily_km_limit,
        "long_halt_minutes": settings.long_halt_minutes,
        "min_stop_minutes": settings.min_stop_minutes,
        "stale_gps_minutes": settings.stale_gps_minutes,
        "expire_soon_days": settings.expire_soon_days,
        "expire_watch_days": settings.expire_watch_days,
        "approach_ratio": settings.approach_ratio,
        "operating_start_hour": settings.operating_start_hour,
        "operating_end_hour": settings.operating_end_hour,
        "live_snapshot_minutes": LIVE_SNAPSHOT_MINUTES,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        "updated_by": updater,
        "defaults": dict(PLATFORM_DEFAULTS),
    }


def save_platform_settings(validated_data, user=None):
    settings = get_platform_settings()
    for field, value in validated_data.items():
        setattr(settings, field, value)
    settings.updated_by = user
    settings.save()
    clear_platform_settings_cache()
    return get_platform_settings()


def reset_platform_settings(user=None):
    return save_platform_settings(dict(PLATFORM_DEFAULTS), user=user)
