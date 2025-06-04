# Copy this code into a python manage.py shell when you're ready

import csv
import json
from adaptivetest.models import QuestionBank

with open('improved_question_bank.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        try:
            question = QuestionBank(
                text=row['text'],
                choices=json.loads(row['choices']),  # Convert string to dict
                correct_answer=row['correct_answer'],
                discrimination=float(row['discrimination']),
                difficulty=float(row['difficulty']),
                guessing=float(row['guessing']),
            )
            question.save()
            print(f"Imported: {question.text[:30]}...")
        except Exception as e:
            print(f"Error importing row: {row}")
            print(e)

print("success")
