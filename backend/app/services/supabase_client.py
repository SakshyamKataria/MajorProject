import logging
import threading
import httpx
from supabase import create_client, Client, ClientOptions
from app.core.config import settings

logger = logging.getLogger(__name__)

_thread_local = threading.local()


def get_supabase_admin() -> Client:
    """
    Returns a thread-local Supabase client configured with the service role key.
    Uses HTTP/1.1 (http2=False) to prevent HTTP/2 multiplexing collisions and
    RemoteProtocolError ('Server disconnected') during concurrent background tasks
    and status-polling requests.
    """
    if not hasattr(_thread_local, "client"):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in .env")

        http_client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=10.0,
            ),
        )
        options = ClientOptions(httpx_client=http_client)
        _thread_local.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            options=options,
        )
    return _thread_local.client
