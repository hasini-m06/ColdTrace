"""
backend/routers/alerts_router.py
---------------------------------
Protected alert subscription endpoints.
All routes require a valid JWT access_token cookie (get_current_user dependency).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from database.db import fetch_all, fetch_one, execute_query
from routers.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class SubscribeRequest(BaseModel):
    location_id: Optional[int] = None  # None = subscribe to all high-risk alerts


# ---------------------------------------------------------------------------
# POST /alerts/subscribe
# ---------------------------------------------------------------------------
@router.post("/subscribe")
def subscribe(body: SubscribeRequest, current_user: dict = Depends(get_current_user)):
    """
    Subscribe the current user to risk alerts for a specific location (or all
    locations if location_id is omitted).
    Silently succeeds if an identical subscription already exists (idempotent).
    """
    user_id     = current_user["id"]
    location_id = body.location_id

    # Validate location_id if provided
    if location_id is not None:
        loc = fetch_one("SELECT id FROM locations WHERE id = ?", (location_id,))
        if not loc:
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found.")

    # Check for duplicate subscription
    existing = fetch_one(
        """SELECT id FROM alert_preferences
           WHERE user_id = ?
             AND (location_id = ? OR (location_id IS NULL AND ? IS NULL))""",
        (user_id, location_id, location_id),
    )
    if existing:
        return {"message": "Already subscribed.", "preference_id": existing["id"]}

    execute_query(
        "INSERT INTO alert_preferences (user_id, location_id, channel) VALUES (?, ?, 'email')",
        (user_id, location_id),
    )

    # Fetch the newly created row's id
    new_pref = fetch_one(
        """SELECT id FROM alert_preferences
           WHERE user_id = ?
             AND (location_id = ? OR (location_id IS NULL AND ? IS NULL))
           ORDER BY id DESC LIMIT 1""",
        (user_id, location_id, location_id),
    )

    scope = f"location {location_id}" if location_id else "all high-risk locations"
    return {
        "message": f"Subscribed to alerts for {scope}.",
        "preference_id": new_pref["id"] if new_pref else None,
    }


# ---------------------------------------------------------------------------
# DELETE /alerts/subscribe/{preference_id}
# ---------------------------------------------------------------------------
@router.delete("/subscribe/{preference_id}")
def unsubscribe(preference_id: int, current_user: dict = Depends(get_current_user)):
    """
    Remove a subscription. Only succeeds if the preference belongs to the
    current user (prevents users from deleting each other's subscriptions).
    """
    pref = fetch_one(
        "SELECT * FROM alert_preferences WHERE id = ?", (preference_id,)
    )
    if not pref:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    if pref["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your subscription.")

    execute_query("DELETE FROM alert_preferences WHERE id = ?", (preference_id,))
    return {"message": "Unsubscribed successfully."}


# ---------------------------------------------------------------------------
# GET /alerts/my-subscriptions
# ---------------------------------------------------------------------------
@router.get("/my-subscriptions")
def my_subscriptions(current_user: dict = Depends(get_current_user)):
    """
    List all alert subscriptions for the current user, with location names joined.
    location_name is null for "subscribe to all" preferences.
    """
    rows = fetch_all(
        """SELECT ap.id, ap.location_id, ap.channel, ap.created_at,
                  l.name  AS location_name,
                  l.district AS location_district
           FROM alert_preferences ap
           LEFT JOIN locations l ON ap.location_id = l.id
           WHERE ap.user_id = ?
           ORDER BY ap.created_at DESC""",
        (current_user["id"],),
    )
    # Annotate None location_id rows clearly
    for row in rows:
        if row["location_id"] is None:
            row["scope"] = "all_locations"
        else:
            row["scope"] = "specific_location"
    return rows


# ---------------------------------------------------------------------------
# GET /alerts/history
# ---------------------------------------------------------------------------
@router.get("/history")
def alert_history(current_user: dict = Depends(get_current_user)):
    """
    Return recent alert records for locations the current user is subscribed to.
    Includes alerts from both specific-location subscriptions and any
    "subscribe to all" (location_id IS NULL) subscriptions.
    """
    user_id = current_user["id"]

    # Check if user has a wildcard (all-locations) subscription
    has_wildcard = fetch_one(
        """SELECT id FROM alert_preferences
           WHERE user_id = ? AND location_id IS NULL""",
        (user_id,),
    )

    if has_wildcard:
        # Return all alerts
        rows = fetch_all(
            """SELECT a.id, a.score, a.timestamp, a.message,
                      l.id AS location_id, l.name, l.district
               FROM alerts a
               JOIN locations l ON a.location_id = l.id
               ORDER BY a.timestamp DESC
               LIMIT 100"""
        )
    else:
        # Return alerts only for subscribed locations
        rows = fetch_all(
            """SELECT a.id, a.score, a.timestamp, a.message,
                      l.id AS location_id, l.name, l.district
               FROM alerts a
               JOIN locations l ON a.location_id = l.id
               WHERE a.location_id IN (
                   SELECT location_id FROM alert_preferences
                   WHERE user_id = ? AND location_id IS NOT NULL
               )
               ORDER BY a.timestamp DESC
               LIMIT 100""",
            (user_id,),
        )

    return rows
