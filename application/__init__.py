import time
import sqlite3
import serial
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

from .routes import *

# Import the shared serial_port variable
from .serial import serial_port

# Initialize the serial connection for SMS
if serial_port is None:
    print("No valid serial port found. SMS functionality will be disabled.")

def send_sms(phone_number, message):
    if serial_port is None:
        print("Serial port is not available. Cannot send SMS.")
        return

    try:
        serial_port.write(f'AT+CMGS="{phone_number}"\r'.encode())
        serial_port.flush()
        serial_port.write(f'{message}\x1A'.encode())  # Ctrl+Z ends the message
        serial_port.flush()
        print(f"SMS sent to {phone_number}: {message}")
    except Exception as e:
        print(f"Error sending SMS: {e}")

def process_incoming_sms():
    if serial_port is None:
        print("Serial port is not available. Cannot process incoming SMS.")
        return

    while True:
        try:
            if serial_port.in_waiting > 0:
                sms = serial_port.readline().decode('utf-8').strip()
                if sms.startswith("+CMT:"):  # Incoming SMS
                    # Extract the phone number and message content
                    parts = sms.split(',')
                    phone_number = parts[1].strip('"')
                    message_content = serial_port.readline().decode('utf-8').strip()

                    # Process the message
                    if message_content.upper() == "LIST":
                        # Send a list of polls
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, title FROM surveys")
                        polls = cursor.fetchall()
                        conn.close()

                        response = "Available Polls:\n"
                        for poll in polls:
                            response += f"{poll['id']}: {poll['title']}\n"
                        response += "To vote, send: VOTE <poll_id> <option>"

                        send_sms(phone_number, response)

                    elif message_content.upper().startswith("VOTE"):
                        # Process the vote
                        try:
                            _, poll_id, option = message_content.split()
                            poll_id = int(poll_id)
                            option = option.strip()

                            conn = get_db_connection()
                            cursor = conn.cursor()

                            # Check if the phone number has already voted for this poll
                            cursor.execute("""
                                SELECT r.id 
                                FROM responses r
                                JOIN questions q ON r.question_id = q.id
                                WHERE r.phone_number = ? AND q.survey_id = ?
                            """, (phone_number, poll_id))
                            existing_vote = cursor.fetchone()

                            if existing_vote:
                                send_sms(phone_number, "You have already voted in this poll.")
                                conn.close()
                                continue

                            # Fetch the question_id for the selected poll and option
                            cursor.execute("""
                                SELECT id FROM questions 
                                WHERE survey_id = ? AND question_text = ?
                            """, (poll_id, option))
                            question = cursor.fetchone()

                            if not question:
                                send_sms(phone_number, "Invalid vote option.")
                                conn.close()
                                continue

                            question_id = question['id']

                            # Insert the vote into the responses table
                            cursor.execute("""
                                INSERT INTO responses (phone_number, question_id, response) 
                                VALUES (?, ?, ?)
                            """, (phone_number, question_id, option))
                            conn.commit()
                            conn.close()

                            send_sms(phone_number, "Vote submitted successfully!")
                        except Exception as e:
                            send_sms(phone_number, "Invalid vote format. Use: VOTE <poll_id> <option>")
        except Exception as e:
            print(f"Error processing incoming SMS: {e}")
            break

        time.sleep(1)  # Poll for new SMS every second