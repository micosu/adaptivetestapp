# Adaptive Testing Webapp

# First-time Setup Instructions

This guide will walk you through how to set up and try out the adaptive testing app locally. The following commands should be run in your terminal.

## 1. Clone the repo:

    ```bash
    git clone https://github.com/micosu/adaptivetestapp.git
    cd adaptivetestapp
    ```

## 2. Create and activate a virtual environment:

### On Mac

    ```bash
    python3 -m venv venv OR python -m venv venv (try both, see which works)
    source venv/bin/activate
    ```

### On Windows:

    ```bash
    python -m venv venv
    source venv\Scripts\activate
    ```

## 3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## 4. Run migrations:

    ```bash
    python manage.py migrate
    ```

## 5. Set-up Question Database

First, run the following command:
`bash
    python manage.py shell
    `

Then, open "make_question_bank.py" and copy the entire file and paste it into your terminal window.
If it runs successfully, it should print the "success" message without any errors.

## 5. Run the server:

```bash
python manage.py runserver
```

## 6. Open in browser

Visit `http://127.0.0.1:8000` in your browser.

# General Use

## Virtual Environment

Whenever you run any of these commands, you must be in a virtual environment for this to work. In your terminal, it should start
with something like (venv) or (pyenv) indicating that you are in a virtual environment. If you are not, make sure you are in adaptivetestapp folder, and run the following command:

(Mac) source venv\Scripts\activate
(Windows) source venv\Scripts\activate

# Creating a Feature Branch

1. **Create a New Feature Branch**:

   - Always create a new branch from `main` for your feature. Use the following commands:
     ```bash
     git checkout main
     git pull origin main
     git checkout -b feature/<your-feature-name>
     ```

2. **Work on Your Feature**:

   - Make the necessary changes for your feature.
   - Commit your changes regularly with clear and concise messages:
     ```bash
     git add .
     git commit -m "Feature <your-feature-name>: <commit-message>"
     ```

   Example commit command:

   ```bash
    git add .
    git commit -m "Feature changehtml: Added css files for html"
   ```

3. **Push Your Feature Branch**:
   - Once you're done working on your feature, push your branch to GitHub:
     ```bash
     git push origin feature/<your-feature-name>
     ```
