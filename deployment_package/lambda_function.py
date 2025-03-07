import logging
from reminder import check_due_tasks
import json



def lambda_handler(event, context):
    """
    AWS Lambda function to check due tasks and send reminders.
    """
    logging.info("Lambda function started: Checking due tasks")

    try:

        response = check_due_tasks()
        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }

    except Exception as e:
        logging.error(f"Lambda execution error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }





