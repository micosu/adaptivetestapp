# Adaptive Testing Webapp

# First-time Setup Instructions

This guide will walk you through how to set up and try out the adaptive testing app locally. The following commands should be run in your terminal.

## 1. Clone the repo:

git clone https://github.com/micosu/adaptivetestapp.git

cd adaptivetestapp

## 2. Create and activate a virtual environment:

### On Mac

python3 -m venv venv OR python -m venv venv (try both, see which works)

source venv/bin/activate

### On Windows:

python -m venv venv

source venv\Scripts\activate

## 3. Install dependencies:

pip install -r requirements.txt

## 4. Run migrations:

python manage.py migrate

## 5. Set-up Question Database

First, run the following command:

python manage.py shell

Then, open "make_question_bank.py" and copy the entire file and paste it into your terminal window.
If it runs successfully, it should print the "success" message without any errors.

## 5. Run the server:

python manage.py runserver

## 6. Open in browser

Visit `http://127.0.0.1:8000` in your browser.

# General Use

## Virtual Environment

Whenever you run any of these commands, you must be in a virtual environment for this to work. In your terminal, it should start
with something like (venv) or (pyenv) indicating that you are
