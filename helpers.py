import logging
from typing import Optional

import requests
from dateutil import tz

from db_connections import get_main_crm_connection


def convert_utc_to_local(utc_datetime, user_time_zone):
    """
    Converts a UTC datetime object to the user's local timezone.

    :param utc_datetime: A timezone-aware or naive UTC datetime object.
    :param user_time_zone: The user's timezone as a string (e.g., "America/New_York").
    :return: A timezone-aware datetime object in the user's timezone.
    """
    if not utc_datetime:
        return None

    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=tz.tzutc())

    to_zone = tz.gettz(user_time_zone) or tz.tzutc()

    return utc_datetime.astimezone(to_zone)


def get_user_basic_info_raw(user_id):
    """
    Retrieves first_name, last_name, email, timezone for a user from the 'users' table.
    Returns a dictionary or None if not found.
    """
    db_connection = get_main_crm_connection()
    user_id_str = str(user_id)

    try:
        with db_connection.cursor() as cursor:
            cursor.execute("""
                SELECT first_name, last_name, email, timezone
                FROM users
                WHERE id = %s
            """, (user_id_str,))
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "first_name": row[0],
                "last_name": row[1],
                "email": row[2],
                "timezone": row[3] if row[3] else "UTC"
            }
    except Exception as e:
        logging.error(f"Error fetching user info for {user_id}: {e}")
        return None
    finally:
        db_connection.close()


def get_contact_basic_info_raw(contact_id):
    """
    Retrieves first_name, last_name, email, phone for a contact from the 'contacts' table.
    Returns a dictionary or None if not found.
    """
    db_connection = get_main_crm_connection()
    contact_id_str = str(contact_id)

    try:
        with db_connection.cursor() as cursor:
            cursor.execute("""
                SELECT first_name, last_name, email, phone
                FROM contacts
                WHERE id = %s
            """, (contact_id_str,))
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "first_name": row[0] or "",
                "last_name": row[1] or "",
                "email": row[2] or "",
                "phone": row[3] or ""
            }
    except Exception as e:
        logging.error(f"Error fetching contact info for {contact_id}: {e}")
        return None
    finally:
        db_connection.close()


def send_task_reminder_email(
        tenant_id: str,
        contact_id: str,
        payload: dict,
        api_key: Optional[str] = None,
) -> dict:
    """
    Sends a task reminder email via the email service.

    :param tenant_id: The tenant's ID (string or UUID as a string).
    :param contact_id: The contact's ID (string or UUID as a string).
    :param payload: A dictionary matching TaskReminderPayload fields.
    :param api_key: (Optional) an API key if the service requires an auth header.

    :return: A dictionary with either the success response or an error message.
    """
    base_url = "https://impala-email-services-8c3f29db6792.herokuapp.com/api/emails"
    route_url = f"{base_url}/tenants/{tenant_id}/contacts/{contact_id}/tasks/reminder"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    response = None

    try:
        response = requests.post(url=route_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        try:
            return response.json()
        except requests.JSONDecodeError:
            logging.error(f"Failed to decode JSON response: {response.text}")
            return {"error": "Invalid JSON response from email service", "status_code": response.status_code}

    except requests.RequestException as e:
        error_message = f"Error calling email service: {e}"

        if response is not None:
            error_message += f", Response: {response.text}"

        logging.error(error_message)
        return {"error": error_message,
                "status_code": response.status_code if response else None}
