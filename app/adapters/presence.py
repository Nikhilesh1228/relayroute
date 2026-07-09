from contextlib import suppress
from typing import Any, cast

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

GEO_KEY = "relayroute:couriers:geo"


def _client() -> Redis | None:
    url = get_settings().redis_url
    return Redis.from_url(url, decode_responses=True, socket_timeout=0.2) if url else None


def update_location(courier_id: str, latitude: float, longitude: float) -> None:
    client = _client()
    if client:
        with suppress(RedisError):
            client.geoadd(GEO_KEY, [longitude, latitude, courier_id])
            client.setex(f"relayroute:courier:{courier_id}:online", 90, "1")


def nearby_couriers(latitude: float, longitude: float, radius_km: float) -> list[tuple[str, float]]:
    client = _client()
    if client is None:
        return []
    try:
        results = cast(
            list[tuple[Any, Any]],
            client.geosearch(
                GEO_KEY,
                longitude=longitude,
                latitude=latitude,
                radius=radius_km,
                unit="km",
                withdist=True,
                sort="ASC",
                count=20,
            ),
        )
        return [(str(item[0]), float(item[1])) for item in results]
    except RedisError:
        return []
