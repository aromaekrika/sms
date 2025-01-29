from flask import Flask, render_template, request, jsonify
import sqlite3
import serial
import config

app = Flask(__name__)

DATABASE = 'database/sms_survey.db'
#serial_port = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=1)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_survey', methods=['GET', 'POST'])
def create_survey():
    if request.method == 'POST':
        title = request.form.get('title')
        questions = request.form.get('questions', '').split(',')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO surveys (title) VALUES (?)", (title,))
        survey_id = cursor.lastrowid
        
        for question in questions:
            cursor.execute("INSERT INTO questions (survey_id, question_text) VALUES (?, ?)", (survey_id, question.strip()))
        
        conn.commit()
        conn.close()
        return render_template('create_survey.html', message="Survey created successfully!")
    return render_template('create_survey.html')

@app.route('/send_survey', methods=['GET', 'POST'])
def send_survey():
    if request.method == 'POST':
        survey_id = request.form.get('survey_id')
        phone_numbers = request.form.get('phone_numbers', '').split(',')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question_text FROM questions WHERE survey_id = ?", (survey_id,))
        questions = cursor.fetchall()
        
        if not questions:
            return render_template('send_survey.html', error="Invalid Survey ID")
        
        for phone_number in phone_numbers:
            for question in questions:
                send_sms(phone_number.strip(), question['question_text'])
        
        return render_template('send_survey.html', message="Survey sent successfully!")
    return render_template('send_survey.html')

@app.route('/view_responses', methods=['GET'])
def view_responses():
    survey_id = request.args.get('survey_id')
    
    if survey_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.phone_number, r.response 
            FROM responses r 
            JOIN questions q ON r.question_id = q.id 
            WHERE q.survey_id = ?
        """, (survey_id,))
        responses = cursor.fetchall()
        conn.close()
        return render_template('view_responses.html', responses=responses)
    
    return render_template('view_responses.html', responses=None)

def send_sms(phone_number, message):
    serial_port.write(f'AT+CMGS="{phone_number}"\r'.encode())
    serial_port.flush()
    serial_port.write(f'{message}\x1A'.encode())  # Ctrl+Z ends the message
    serial_port.flush()

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT,debug=True)
