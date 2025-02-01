
from flask import render_template, request
from . import app
from .database import get_db_connection
from .serial import serial_port, get_phone_number  # Import the shared serial_port and get_phone_number

@app.route('/')
def index():
    # Check if the serial port is available
    serial_available = serial_port is not None

    # Fetch the phone number from the GSM modem
    phone_number = get_phone_number() if serial_available else None

    # Define SMS voting instructions
    if phone_number:
        sms_instructions = (
            "To vote by SMS:\n"
            "1. Send 'LIST' to {phone_number} to view available polls.\n"
            "2. Send 'VOTE <poll_id> <option>' to {phone_number} to vote.\n"
            "Example: VOTE 1 Emmanuel O."
        ).format(phone_number=phone_number)
    else:
        sms_instructions = (
            "SMS voting is currently unavailable.\n"
            "Please ensure the GSM modem is connected and has a valid SIM card."
        )

    # Define error message if serial port is not available
    error_message = None
    if not serial_available:
        error_message = "No valid serial port found. SMS functionality will be disabled."

    # Render the template with the data
    return render_template(
        'index.html',
        serial_available=serial_available,
        phone_number=phone_number,
        sms_instructions=sms_instructions,
        error_message=error_message
    )

@app.route('/create_poll', methods=['GET', 'POST'])
def create_poll():
    if request.method == 'POST':
        poll_title = request.form.get('poll_title')
        poll_options = request.form.get('poll_options', '').split(',')

        if not poll_title or not poll_options:
            return render_template('create_poll.html', error="Please fill out all fields.")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if a poll with the same title already exists
        cursor.execute("SELECT id FROM surveys WHERE title = ?", (poll_title,))
        existing_poll = cursor.fetchone()

        if existing_poll:
            conn.close()
            return render_template('create_poll.html', error="A poll with this title already exists.")

        # Insert the new poll into the surveys table
        cursor.execute("INSERT INTO surveys (title) VALUES (?)", (poll_title,))
        survey_id = cursor.lastrowid

        # Insert the poll options into the questions table
        for poll_option in poll_options:
            if poll_option.strip():  # Ensure the option is not empty
                cursor.execute("INSERT INTO questions (survey_id, question_text) VALUES (?, ?)", (survey_id, poll_option.strip()))

        try:
            conn.commit()
            conn.close()
            return render_template('create_poll.html', message=f"{poll_title} poll created successfully!")
        except Exception as e:
            conn.close()
            return render_template('create_poll.html', error="An error occurred while creating the poll.")

    # Handle GET request
    return render_template('create_poll.html')

@app.route('/submit_vote', methods=['GET', 'POST'])
def submit_vote():
    # Fetch poll_titles and poll_options (common for both GET and POST)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, id FROM surveys")
    titles = cursor.fetchall()

    cursor2 = conn.cursor()
    cursor2.execute("SELECT survey_id, question_text FROM questions")
    polls = cursor2.fetchall()
    conn.close()

    # Transform poll_titles into a list of dictionaries
    poll_titles = []
    for title in titles:
        try:
            poll_detail = {title[0]: title[1]}
            poll_titles.append(poll_detail)
        except:
            pass

    # Transform poll_options into a dictionary of arrays
    poll_options = {}
    for poll in polls:
        try:
            survey_id = poll[0]
            question_text = poll[1]
            if survey_id not in poll_options:
                poll_options[survey_id] = []
            poll_options[survey_id].append(question_text)
        except:
            pass

    if request.method == 'POST':
        survey_id = request.form.get('poll_id')
        phone_number = request.form.get('phone_number')
        vote_option = request.form.get('vote_option')

        if not survey_id or not phone_number or not vote_option:
            return render_template('submit_vote.html', error="Please fill out all fields.", poll_titles=poll_titles, poll_options=poll_options)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the phone number has already voted for this poll
        cursor.execute("""
            SELECT r.id 
            FROM responses r
            JOIN questions q ON r.question_id = q.id
            WHERE r.phone_number = ? AND q.survey_id = ?
        """, (phone_number, survey_id))
        existing_vote = cursor.fetchone()

        if existing_vote:
            conn.close()
            return render_template('submit_vote.html', error="You have already voted in this poll.", poll_titles=poll_titles, poll_options=poll_options)

        # Fetch the question_id for the selected poll and vote option
        cursor.execute("""
            SELECT id FROM questions 
            WHERE survey_id = ? AND question_text = ?
        """, (survey_id, vote_option))
        question = cursor.fetchone()

        if not question:
            conn.close()
            return render_template('submit_vote.html', error="Invalid vote option.", poll_titles=poll_titles, poll_options=poll_options)

        question_id = question['id']

        # Insert the vote into the responses table
        try:
            cursor.execute("""
                INSERT INTO responses (phone_number, question_id, response) 
                VALUES (?, ?, ?)
            """, (phone_number, question_id, vote_option))
            conn.commit()
            conn.close()
            return render_template('submit_vote.html', message="Vote submitted successfully!", poll_titles=poll_titles, poll_options=poll_options)
        except Exception as e:
            conn.close()
            return render_template('submit_vote.html', error="An error occurred while submitting your vote.", poll_titles=poll_titles, poll_options=poll_options)

    # Handle GET request
    return render_template('submit_vote.html', poll_titles=poll_titles, poll_options=poll_options)


@app.route('/view_responses', methods=['GET'])
def view_responses():
    survey_id = request.args.get('survey_id')
    
    # Fetch all polls
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM surveys")
    polls = cursor.fetchall()
    
    # Fetch responses and calculate vote tallies for the selected survey_id
    responses = None
    vote_tallies = None
    leading_option = None
    if survey_id:
        # Fetch all responses for the selected survey
        cursor.execute("""
            SELECT r.response 
            FROM responses r 
            JOIN questions q ON r.question_id = q.id 
            WHERE q.survey_id = ?
        """, (survey_id,))
        responses = cursor.fetchall()

        # Calculate vote tallies
        vote_tallies = {}
        for response in responses:
            option = response['response']
            if option in vote_tallies:
                vote_tallies[option] += 1
            else:
                vote_tallies[option] = 1

        # Identify the leading option
        if vote_tallies:
            leading_option = max(vote_tallies, key=vote_tallies.get)
    
    conn.close()
    
    # Render the template with polls, responses, vote tallies, and leading option
    return render_template(
        'view_responses.html',
        polls=polls,
        responses=responses,
        vote_tallies=vote_tallies,
        leading_option=leading_option,
        survey_id=survey_id
    )


