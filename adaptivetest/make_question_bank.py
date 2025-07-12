# Copy this code into a python manage.py shell when you're ready

import csv
import json
from adaptivetest.models import QuestionBank

with open('synonym_question_bank_v5.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        try:
            question = QuestionBank(
                text=row['text'],
                choices=json.loads(row['choices']),  # Convert string to dict
                correct_answer=row['correct_answer'],
                antonym = row['antonym'],
                unrelated = row['unrelated'],
                discrimination=float(row['discrimination']),
                difficulty=float(row['difficulty']),
                guessing=float(row['guessing']),
                question_type="syn",
            )
            question.save()
            print(f"Imported: {question.text[:30]}...")
        except Exception as e:
            print(f"Error importing row: {row}")
            print(e)

print("Success importing synonym questions")

with open('wic_question_bank_v5.csv', newline='', encoding='utf-8') as csvfile:
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
                question_type="wic",
            )
            question.save()
            print(f"Imported: {question.text[:30]}...")
        except Exception as e:
            print(f"Error importing row: {row}")
            print(e)

print("Success importing word in context questions")