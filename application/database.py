
import sqlite3


DATABASE = 'database/sms_survey.db'
#serial_port = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
