import datetime
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from db_connections import get_task_db_connection
from helpers import get_user_basic_info_raw, get_contact_basic_info_raw, convert_utc_to_local, send_task_reminder_email

load_dotenv()


def check_due_tasks():
    """
    Checks and sends reminders for due tasks.
    """
    logging.info("Executing check_due_tasks()...")

    task_db_conn = get_task_db_connection()
    tasks_processed = []

    try:
        with task_db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, user_id, contact_id, tenant_id, title, description, due_at, reminder_at
                FROM tasks
                WHERE reminder_sent = false
                  AND reminder_at <= NOW()
            """)
            tasks_due = cursor.fetchall()

        if not tasks_due:
            logging.info("No tasks due for reminders at this time.")
            return {
                "status": "success",
                "message": "No due tasks found."
            }

        for row in tasks_due:
            try:
                (
                    task_id, user_id, contact_id, tenant_id,
                    task_title, task_description, due_at, reminder_at
                ) = row

                logging.info(f"Processing task: {task_id}")

                user_info = get_user_basic_info_raw(user_id)
                if not user_info:
                    logging.warning(f"User {user_id} not found. Skipping task {task_id}.")
                    continue

                user_timezone = user_info.get("timezone", "UTC")
                local_due_datetime = convert_utc_to_local(due_at, user_timezone)
                local_now_datetime = convert_utc_to_local(datetime.datetime.utcnow(), user_timezone)

                if local_due_datetime.date() == local_now_datetime.date() and local_now_datetime >= local_due_datetime:
                    contact_info = get_contact_basic_info_raw(contact_id)
                    if not contact_info:
                        logging.warning(f"Contact {contact_id} not found. Skipping task {task_id}.")
                        continue

                    task_reminder_payload = {
                        "task_title": task_title,
                        "task_description": task_description or "",
                        "user_name": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip(),
                        "user_email": user_info.get("email", ""),
                        "contact_name": " ".join(filter(None, [contact_info.get("first_name", ""),
                                                               contact_info.get("last_name", "")])).title(),
                        "contact_email": contact_info.get("email", "") or "",
                        "contact_phone": contact_info.get("phone", "") or ""
                    }

                    api_key = os.getenv('API_KEY')
                    if not api_key:
                        logging.error("API Key is missing. Cannot send email reminders.")
                        return {
                            "status": "error",
                            "message": "API Key is missing."
                        }

                    try:
                        response = send_task_reminder_email(
                            tenant_id=str(tenant_id),
                            contact_id=str(contact_id),
                            payload=task_reminder_payload,
                            api_key=api_key
                        )
                        logging.info(f"Reminder sent for task_id={task_id}: {response}")
                        tasks_processed.append({"task_id": task_id, "status": "reminder sent"})

                    except Exception as email_error:
                        logging.error(f"Failed to send reminder for task_id={task_id}: {email_error}")
                        tasks_processed.append({"task_id": task_id, "status": "failed to send reminder"})
                        continue

                    try:
                        with task_db_conn.cursor() as update_cursor:
                            update_cursor.execute("UPDATE tasks SET reminder_sent = true WHERE id = %s", (task_id,))
                        task_db_conn.commit()
                    except Exception as e:
                        logging.error(f"Failed to update reminder_sent for task {task_id}: {str(e)}")

            except Exception as task_error:
                logging.error(f"Error processing task: {str(task_error)}")

        logging.info("Done processing all due tasks.")

    except Exception as e:
        logging.error(f"Error in check_due_tasks: {str(e)}")

    finally:
        task_db_conn.close()

    return {
        "status": "success",
        "tasks_processed": tasks_processed
    }
