import logging
import urllib.parse
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.api.meetings import validate_uuid
from app.services.calendar_service import (
    generate_authorization_url,
    parse_oauth_state,
    exchange_code_and_store_tokens,
    get_user_calendar_status,
)
from app.services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Google Calendar"])


@router.get("/authorize", summary="Redirects to Google Calendar OAuth consent screen")
def authorize_calendar(
    user_id: Optional[str] = Query(None, description="Supabase user UUID. Defaults to configured default user."),
    redirect: bool = Query(True, description="Whether to return a 307 Redirect or a JSON payload with the auth URL."),
):
    """
    Step 1 of Google Calendar OAuth flow:
    Generates the Google OAuth authorization URL requesting offline access
    and the 'https://www.googleapis.com/auth/calendar.events' scope.
    Redirects the browser directly to Google's consent screen.
    """
    target_user_id = user_id if user_id else settings.DEFAULT_USER_ID
    validate_uuid(target_user_id, "user_id")

    try:
        auth_url, _ = generate_authorization_url(target_user_id)
    except ValueError as val_err:
        logger.error(f"Configuration error initializing OAuth flow: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(val_err),
        )
    except Exception as e:
        logger.error(f"Failed to generate Google Calendar auth URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate authorization URL: {str(e)}",
        )

    if redirect:
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return {"authorization_url": auth_url, "user_id": target_user_id}


@router.get("/callback", summary="OAuth callback receiving authorization code from Google")
def calendar_callback(
    code: Optional[str] = Query(None, description="Google OAuth authorization code"),
    state: Optional[str] = Query(None, description="OAuth state parameter containing encoded user context"),
    error: Optional[str] = Query(None, description="Error code from Google consent rejection"),
    error_description: Optional[str] = Query(None, description="Error description from Google"),
):
    """
    Step 2 of Google Calendar OAuth flow:
    Receives authorization code, exchanges it for access & refresh tokens via google-auth-oauthlib,
    persists tokens into public.calendar_tokens table in Supabase,
    and redirects the user back to the frontend application.
    """
    # 1. Handle error response from Google (e.g. user dismissed or cancelled consent)
    if error:
        err_msg = error_description or error
        logger.warning(f"Google OAuth consent rejected/failed: {err_msg}")
        redirect_url = f"{settings.FRONTEND_URL}/?calendar_error={urllib.parse.quote(err_msg)}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization 'code' parameter in Google OAuth callback.",
        )

    # 2. Extract user_id and PKCE code_verifier from OAuth state parameter
    user_id, code_verifier = parse_oauth_state(state)
    validate_uuid(user_id, "user_id")

    # 3. Exchange authorization code for tokens and persist in Supabase
    try:
        exchange_code_and_store_tokens(code=code, user_id=user_id, code_verifier=code_verifier)
        logger.info(f"Google Calendar connected successfully for user {user_id}")
        redirect_url = f"{settings.FRONTEND_URL}/?calendar_connected=true"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except Exception as e:
        logger.error(f"Failed to exchange Google OAuth code for user {user_id}: {e}", exc_info=True)
        redirect_url = f"{settings.FRONTEND_URL}/?calendar_error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/status", summary="Check whether user has connected Google Calendar")
def calendar_status(
    user_id: Optional[str] = Query(None, description="User UUID to check. Defaults to active user."),
):
    """
    Step 3:
    Queries public.calendar_tokens to check whether the current user has a connected Google Calendar.
    Returns connection status, token expiration timestamp, and refresh token presence.
    """
    target_user_id = user_id if user_id else settings.DEFAULT_USER_ID
    validate_uuid(target_user_id, "user_id")

    status_data = get_user_calendar_status(target_user_id)
    return status_data


@router.post("/disconnect", summary="Disconnect Google Calendar for user")
def disconnect_calendar(
    user_id: Optional[str] = Query(None, description="User UUID. Defaults to active user."),
):
    """
    Removes calendar tokens for the user from public.calendar_tokens.
    """
    target_user_id = user_id if user_id else settings.DEFAULT_USER_ID
    validate_uuid(target_user_id, "user_id")

    supabase = get_supabase_admin()
    try:
        supabase.table("calendar_tokens").delete().eq("user_id", target_user_id).execute()
        return {
            "success": True,
            "user_id": target_user_id,
            "message": "Google Calendar disconnected successfully.",
        }
    except Exception as e:
        logger.error(f"Failed to disconnect Google Calendar for user {target_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect Google Calendar: {str(e)}",
        )
