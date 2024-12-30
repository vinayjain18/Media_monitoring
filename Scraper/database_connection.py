import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
import yaml

def read_db_config(filename='config.yaml'):
    """Read database configuration from a YAML file."""
    with open(filename, 'r') as f:
        db_config = yaml.safe_load(f)
    return db_config['mysql']

def connect():
    """Connect to MySQL database."""
    try:
        db_config = read_db_config()
        print('Connecting to MySQL database...')
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print('Connected to MySQL database')
            return conn
    except Error as e:
        print(e)
    return None

def disconnect(conn):
    """Disconnect from MySQL database."""
    if conn is not None and conn.is_connected():
        conn.close()
        print('Disconnected from MySQL database')
