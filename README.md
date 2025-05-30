# Adaptive Testing Webapp

## Setup Instructions

This guide will walk you through how to set up and try out the adaptive testing app locally.  The following commands should be run in your terminal.

## 1. Clone the repo:

git clone https://github.com/micosu/adaptivetestapp.git

cd adaptivetestapp

## 2. Create and activate a virtual environment:

### On Mac

python -m venv venv 

source venv/bin/activate

### On Windows:

python -m venv venv 

source venv\Scripts\activate

## 3. Install dependencies:

pip install -r requirements.txt

## 4. Run migrations:

python manage.py migrate

## 5. Run the server:

python manage.py runserver

## 6. Open in browser

Visit `http://127.0.0.1:8000` in your browser.
