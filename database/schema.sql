CREATE TABLE surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id INTEGER,
    question_text TEXT NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES surveys (id)
);

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    phone_number TEXT,
    response TEXT,
    FOREIGN KEY (question_id) REFERENCES questions (id)
);
