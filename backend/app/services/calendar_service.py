import os
import json
import logging
import datetime
import base64
import secrets
import string
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from google.auth.exceptions import RefreshError
from postgrest.exceptions import APIError

from app.core.config import settings
from app.services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

# Allow HTTP redirect in development (e.g. http://localhost:8000/calendar/callback)
if settings.ENVIRONMENT == "development" or "localhost" in settings.GOOGLE_CALENDAR_REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def get_calendar_client_config() -> Dict[str, Any]:
    """
    Constructs Google OAuth 2.0 client configuration dictionary for Flow.from_client_config.
    """
    if not settings.GOOGLE_CALENDAR_CLIENT_ID or not settings.GOOGLE_CALENDAR_CLIENT_SECRET:
        raise ValueError(
            "GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET must be configured in .env"
        )
    return {
        "web": {
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_CALENDAR_REDIRECT_URI],
        }
    }


def create_oauth_flow(state: Optional[str] = None) -> Flow:
    """
    Creates and configures a Google OAuth 2.0 Flow instance.
    """
    client_config = get_calendar_client_config()
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=[settings.GOOGLE_CALENDAR_SCOPE],
        redirect_uri=settings.GOOGLE_CALENDAR_REDIRECT_URI,
        state=state,
    )
    return flow


def generate_authorization_url(user_id: str) -> Tuple[str, str]:
    """
    Generates the Google OAuth authorization URL requesting offline access and calendar.events scope.
    Generates a PKCE code_verifier, sets it on the Flow instance, and encodes both user_id
    and code_verifier into the OAuth state parameter so it round-trips back in the callback.
    """
    flow = create_oauth_flow()
    
    # Generate PKCE code_verifier (128 characters of unreserved URI characters)
    chars = string.ascii_letters + string.digits + "-._~"
    code_verifier = "".join(secrets.choice(chars) for _ in range(128))
    flow.code_verifier = code_verifier

    state_payload = {
        "user_id": user_id,
        "code_verifier": code_verifier,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    state_str = base64.urlsafe_b64encode(json.dumps(state_payload).encode("utf-8")).decode("utf-8")

    auth_url, generated_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Ensures refresh_token is re-issued
        state=state_str,
    )
    return auth_url, generated_state


def parse_oauth_state(state_str: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Extracts (user_id, code_verifier) from the OAuth state parameter.
    Supports URL-safe base64 encoded JSON, plain JSON, and raw string fallback.
    """
    if not state_str:
        return settings.DEFAULT_USER_ID, None

    # 1. Try URL-safe base64 decoded JSON
    try:
        decoded_bytes = base64.urlsafe_b64decode(state_str.encode("utf-8"))
        data = json.loads(decoded_bytes.decode("utf-8"))
        if isinstance(data, dict):
            user_id = str(data.get("user_id") or settings.DEFAULT_USER_ID)
            code_verifier = data.get("code_verifier")
            return user_id, code_verifier
    except Exception:
        pass

    # 2. Try raw JSON
    try:
        data = json.loads(state_str)
        if isinstance(data, dict):
            user_id = str(data.get("user_id") or settings.DEFAULT_USER_ID)
            code_verifier = data.get("code_verifier")
            return user_id, code_verifier
    except Exception:
        pass

    # 3. Fallback to raw string
    if state_str.strip():
        return state_str.strip(), None

    return settings.DEFAULT_USER_ID, None


def exchange_code_and_store_tokens(
    code: str, user_id: str, code_verifier: Optional[str] = None
) -> Dict[str, Any]:
    """
    Exchanges the authorization code with Google for access and refresh tokens,
    using the round-tripped PKCE code_verifier, then stores/upserts them
    into public.calendar_tokens for the specified user.
    """
    flow = create_oauth_flow()
    if code_verifier:
        flow.code_verifier = code_verifier

    flow.fetch_token(code=code, code_verifier=code_verifier)
    credentials = flow.credentials


    if not credentials or not credentials.token:
        raise ValueError("Failed to retrieve valid access token from Google OAuth endpoint.")

    # Calculate token expiry
    if credentials.expiry:
        if credentials.expiry.tzinfo is None:
            token_expiry = credentials.expiry.replace(tzinfo=datetime.timezone.utc).isoformat()
        else:
            token_expiry = credentials.expiry.isoformat()
    else:
        # Default 1 hour from now
        token_expiry = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3600)
        ).isoformat()

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    supabase = get_supabase_admin()

    # Check if a refresh token already exists in case Google did not supply one on re-auth
    existing_refresh_token = None
    try:
        existing_res = (
            supabase.table("calendar_tokens")
            .select("refresh_token")
            .eq("user_id", user_id)
            .execute()
        )
        if existing_res.data and len(existing_res.data) > 0:
            existing_refresh_token = existing_res.data[0].get("refresh_token")
    except Exception as e:
        logger.warning(f"Could not inspect existing calendar tokens for user {user_id}: {e}")

    final_refresh_token = credentials.refresh_token or existing_refresh_token

    upsert_payload = {
        "user_id": user_id,
        "access_token": credentials.token,
        "token_expiry": token_expiry,
        "connected_at": now_iso,
        "updated_at": now_iso,
    }
    if final_refresh_token:
        upsert_payload["refresh_token"] = final_refresh_token

    res = supabase.table("calendar_tokens").upsert(upsert_payload).execute()
    logger.info(f"Successfully stored Google Calendar tokens for user {user_id}")

    return {
        "user_id": user_id,
        "token_expiry": token_expiry,
        "has_refresh_token": bool(final_refresh_token),
        "data": res.data,
    }


def get_user_calendar_status(user_id: str) -> Dict[str, Any]:
    """
    Queries public.calendar_tokens to determine whether the user has a connected Google Calendar.
    Handles table-missing errors gracefully if migration hasn't been run yet.
    """
    supabase = get_supabase_admin()
    try:
        res = (
            supabase.table("calendar_tokens")
            .select("user_id, token_expiry, connected_at, refresh_token")
            .eq("user_id", user_id)
            .execute()
        )

        if res.data and len(res.data) > 0:
            row = res.data[0]
            return {
                "connected": True,
                "user_id": user_id,
                "connected_at": row.get("connected_at"),
                "token_expiry": row.get("token_expiry"),
                "has_refresh_token": bool(row.get("refresh_token")),
            }
        else:
            return {
                "connected": False,
                "user_id": user_id,
                "connected_at": None,
                "token_expiry": None,
                "has_refresh_token": False,
            }
    except APIError as api_err:
        # PGRST205: relation/table not found in schema cache
        if "PGRST205" in str(api_err) or "calendar_tokens" in str(api_err):
            logger.warning("calendar_tokens table does not exist in database yet.")
            return {
                "connected": False,
                "user_id": user_id,
                "connected_at": None,
                "token_expiry": None,
                "has_refresh_token": False,
                "warning": "Database table 'calendar_tokens' not yet created. Run migration 20260909000000_calendar_tokens.sql in Supabase SQL editor.",
            }
        raise
    except Exception as e:
        logger.error(f"Error querying calendar status for user {user_id}: {e}")
        return {
            "connected": False,
            "user_id": user_id,
            "connected_at": None,
            "token_expiry": None,
            "has_refresh_token": False,
            "error": str(e),
        }


class CalendarReauthRequiredError(HTTPException):
    """Raised when Google Calendar authorization is expired/revoked and user must reauthorize."""
    def __init__(
        self,
        detail: str = "Google Calendar authorization has expired or been revoked. Please reconnect your Google Calendar.",
    ):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_authenticated_credentials(user_id: str) -> Credentials:
    """
    Retrieves and refreshes (if expired) Google OAuth Credentials for a user.
    Accurately checks token_expiry against current time, triggers token refresh via Google OAuth
    when expired or within a 60-second expiration buffer, updates Supabase with the refreshed tokens,
    and raises CalendarReauthRequiredError if the refresh token is revoked/invalid or absent.
    """
    supabase = get_supabase_admin()
    res = (
        supabase.table("calendar_tokens")
        .select("access_token, refresh_token, token_expiry")
        .eq("user_id", user_id)
        .execute()
    )

    if not res.data or len(res.data) == 0:
        raise CalendarReauthRequiredError(
            f"No Google Calendar credentials found for user {user_id}. Please authorize Google Calendar."
        )

    row = res.data[0]
    token = row.get("access_token")
    refresh_token = row.get("refresh_token")
    raw_expiry = row.get("token_expiry")

    if not token:
        raise CalendarReauthRequiredError(
            f"Access token missing for user {user_id}. Please reauthorize Google Calendar."
        )

    # Parse token_expiry into naive UTC datetime for google-auth compatibility
    expiry_dt: Optional[datetime.datetime] = None
    if raw_expiry:
        try:
            parsed_dt = datetime.datetime.fromisoformat(raw_expiry)
            if parsed_dt.tzinfo is not None:
                expiry_dt = parsed_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            else:
                expiry_dt = parsed_dt
        except Exception as parse_err:
            logger.warning(f"Could not parse token_expiry '{raw_expiry}' for user {user_id}: {parse_err}")

    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CALENDAR_CLIENT_ID,
        client_secret=settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        scopes=[settings.GOOGLE_CALENDAR_SCOPE],
        expiry=expiry_dt,
    )

    # Determine if expired (or within a 60-second buffer of expiring)
    now_naive_utc = datetime.datetime.utcnow()
    is_expired = creds.expired or (
        expiry_dt is not None and expiry_dt <= (now_naive_utc + datetime.timedelta(seconds=60))
    )

    if is_expired:
        logger.info(
            f"Detected expired Google Calendar access token for user {user_id} (expiry was: {raw_expiry}). Initiating refresh..."
        )
        if not creds.refresh_token:
            logger.error(f"Cannot refresh token for user {user_id}: no refresh_token stored.")
            raise CalendarReauthRequiredError(
                "Google Calendar access token has expired and no refresh token is stored. Please reauthorize Google Calendar."
            )

        try:
            creds.refresh(Request())
        except RefreshError as refresh_err:
            logger.error(f"Google OAuth rejected refresh token for user {user_id}: {refresh_err}")
            raise CalendarReauthRequiredError(
                "Google Calendar authorization has expired or been revoked. Please reconnect your Google Calendar."
            )
        except Exception as generic_err:
            logger.error(f"Unexpected error refreshing Google Calendar token for user {user_id}: {generic_err}")
            raise CalendarReauthRequiredError(
                f"Failed to refresh Google Calendar token: {str(generic_err)}. Please reauthorize."
            )

        # Update Supabase with refreshed token and new expiry
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if creds.expiry:
            if creds.expiry.tzinfo is None:
                new_expiry_iso = creds.expiry.replace(tzinfo=datetime.timezone.utc).isoformat()
            else:
                new_expiry_iso = creds.expiry.isoformat()
        else:
            new_expiry_iso = (
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3600)
            ).isoformat()

        update_payload = {
            "access_token": creds.token,
            "token_expiry": new_expiry_iso,
            "updated_at": now_iso,
        }
        if creds.refresh_token:
            update_payload["refresh_token"] = creds.refresh_token

        supabase.table("calendar_tokens").update(update_payload).eq("user_id", user_id).execute()
        logger.info(
            f"Successfully refreshed and persisted Google Calendar token for user {user_id} (new expiry: {new_expiry_iso})"
        )

    return creds


def parse_deadline_for_event(raw_deadline: Optional[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses an action item deadline string into Google Calendar start/end datetime or date objects.
    Falls back to tomorrow morning at 09:00 UTC if deadline is not provided or unparseable.
    """
    start_dict: Dict[str, str] = {}
    end_dict: Dict[str, str] = {}

    if raw_deadline:
        try:
            deadline_str = str(raw_deadline).strip()
            if "T" in deadline_str:
                dt = datetime.datetime.fromisoformat(deadline_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                start_dict = {"dateTime": dt.isoformat()}
                end_dict = {"dateTime": (dt + datetime.timedelta(minutes=30)).isoformat()}
            else:
                date_part = deadline_str[:10]
                d = datetime.date.fromisoformat(date_part)
                next_d = d + datetime.timedelta(days=1)
                start_dict = {"date": d.isoformat()}
                end_dict = {"date": next_d.isoformat()}
        except Exception as parse_err:
            logger.warning(f"Could not parse action item deadline '{raw_deadline}', falling back to default: {parse_err}")

    if not start_dict or not end_dict:
        tomorrow = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        start_dt = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        end_dt = start_dt + datetime.timedelta(minutes=30)
        start_dict = {"dateTime": start_dt.isoformat()}
        end_dict = {"dateTime": end_dt.isoformat()}

    return start_dict, end_dict


def create_calendar_event_for_action_item(
    user_id: str,
    action_item: Dict[str, Any],
    meeting_title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Uses user's stored and refreshed Google OAuth credentials to create a calendar event
    for the specified action item via the Google Calendar v3 API.
    """
    creds = get_authenticated_credentials(user_id)
    authed_session = AuthorizedSession(creds)

    task = action_item.get("task") or "Untitled Action Item"
    assignee = action_item.get("assignee")
    priority = (action_item.get("priority") or "medium").upper()
    status_str = action_item.get("status") or "pending"
    raw_deadline = action_item.get("deadline")

    # Format Event Summary
    summary = f"Action Item: {task}"
    if len(summary) > 250:
        summary = summary[:247] + "..."

    # Format Event Description
    desc_lines = []
    if meeting_title:
        desc_lines.append(f"Meeting: {meeting_title}")
    desc_lines.append(f"Task: {task}")
    if assignee:
        desc_lines.append(f"Assignee: {assignee}")
    desc_lines.append(f"Priority: {priority}")
    desc_lines.append(f"Status: {status_str}")
    if raw_deadline:
        desc_lines.append(f"Deadline: {raw_deadline}")
    desc_lines.append("\nCreated by AI Meeting & Lecture Intelligence Platform")
    description = "\n".join(desc_lines)

    # Format Start & End Times
    start_time, end_time = parse_deadline_for_event(raw_deadline)

    event_payload = {
        "summary": summary,
        "description": description,
        "start": start_time,
        "end": end_time,
        "reminders": {
            "useDefault": True,
        },
    }

    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    resp = authed_session.post(url, json=event_payload)

    if resp.status_code not in [200, 201]:
        logger.error(f"Google Calendar API event creation failed ({resp.status_code}): {resp.text}")
        try:
            err_json = resp.json()
            err_msg = err_json.get("error", {}).get("message") or resp.text
        except Exception:
            err_msg = resp.text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Calendar API error: {err_msg}",
        )

    return resp.json()


def delete_calendar_event(user_id: str, event_id: str) -> bool:
    """
    Deletes an event from user's primary Google Calendar by event_id.
    Treats 200, 204, 404, 410 as successful deletion / already removed.
    """
    creds = get_authenticated_credentials(user_id)
    authed_session = AuthorizedSession(creds)
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
    resp = authed_session.delete(url)
    return resp.status_code in [200, 204, 404, 410]

