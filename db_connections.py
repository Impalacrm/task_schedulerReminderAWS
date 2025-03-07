import os
import logging
import pg8000
from urllib.parse import urlparse
from dotenv import load_dotenv




load_dotenv()



def create_db_connection(env_var):

    db_url = os.getenv(env_var)
    if not db_url:
        logging.error(f"{env_var} is not set")
        raise ValueError(f"{env_var} is not set")


    parsed_url = urlparse(db_url)

    try:
        conn= pg8000.connect(
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            database=parsed_url.path.lstrip('/'),
            port=parsed_url.port or 5432,

        )
        return conn

    except Exception as error:
        logging.error(f"Error connecting to {env_var} database: {error}")
        raise


def get_email_db_connection():

    return create_db_connection('EMAIL_DB_URL')

def get_task_db_connection():

    return create_db_connection('TASK_DB_URL')

def get_main_crm_connection():

    return create_db_connection('MAIN_CRM_URL')



