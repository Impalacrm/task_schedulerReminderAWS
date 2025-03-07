import logging
from db_connections import get_task_db_connection
from helpers import get_user_basic_info_raw,get_contact_basic_info_raw,convert_utc_to_local,send_task_reminder_email
from datetime import datetime
import os
import datetime
from dotenv import load_dotenv


load_dotenv()



def check_due_tasks():
    """
    Checks and sends reminders for due tasks.
    """

    task_db_conn = get_task_db_connection()

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
            return

        for row in tasks_due:
            try:
                (
                    task_id, user_id, contact_id, tenant_id,
                    task_title, task_description, due_at, reminder_at
                ) = row


                user_info = get_user_basic_info_raw(user_id)
                if not user_info:
                    logging.warning(f"User {user_id} not found. Skipping task {task_id}.")
                    continue

                user_timezone = user_info.get("timezone","UTC")


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
                        "user_name": f"{user_info['first_name']} {user_info['last_name']}",
                        "user_email": user_info["email"],
                        "contact_name": f"{contact_info['first_name']} {contact_info['last_name']}",
                        "contact_email": contact_info["email"],
                        "contact_phone": contact_info.get("phone")
                    }

                    api_key = os.getenv('API_KEY')
                    if not api_key:
                        logging.error("API Key is missing. Cannot send email reminders.")
                        return

                    try:
                        response = send_task_reminder_email(
                            tenant_id=str(tenant_id),
                            contact_id=str(contact_id),
                            payload=task_reminder_payload,
                            api_key=api_key
                        )
                        logging.info(f"Reminder sent for task_id={task_id}: {response}")
                    except Exception as email_error:
                        logging.error(f"Failed to send reminder for task_id={task_id}: {email_error}")
                        continue


                    try:
                        with task_db_conn.cursor() as update_cursor:
                            update_cursor.execute("UPDATE tasks SET reminder_sent = true WHERE id = %s", (task_id,))
                        task_db_conn.commit()
                    except Exception as e:
                        logging.error(f"Failed to update reminder_sent for task {task_id}: {str(e)}")

            except Exception as task_error:
                logging.error(f"Error processing task : {str(task_error)}")

        logging.info("Done processing all due tasks.")

    except Exception as e:
        logging.error(f"Error in check_due_tasks: {str(e)}")

    finally:
        task_db_conn.close()



