# Adaptive Testing Webapp

# Setup Instructions

## 1. Clone the repo:

git clone https://github.com/micosu/adaptivetestapp.git

cd adaptivetestapp

## 2. Create and activate a virtual environment:

# On Mac

python -m venv venv source venv/bin/activate

# On Windows:

python -m venv venv source venv\Scripts\activate

## 3. Install dependencies:

pip install -r requirements.txt

## 4. Run migrations:

python manage.py migrate

## 5. Run the server:

python manage.py runserver

## 6. Visit `http://127.0.0.1:8000` in your browser.
