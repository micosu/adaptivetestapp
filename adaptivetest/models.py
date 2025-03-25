from django.db import models
from django.contrib.auth.models import User
import numpy as np
from catsim.cat import generate_item_bank
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
from catsim.initialization import FixedPointInitializer
from catsim.stopping import MaxItemStopper

# Create your models here.
class QuestionBank(models.Model):
    text = models.TextField()
    choices = models.JSONField()  # stores options as a dict
    correct_answer = models.CharField(max_length=2)  # 'A', 'B', 'C', etc.

    # IRT parameters
    discrimination = models.FloatField(default=1.0)  # a parameter
    difficulty = models.FloatField()  # b parameter
    guessing = models.FloatField(default=0.0)  # c parameter
    
    def __str__(self):
        return self.text[:50]
    

# Saving questions
# q = Question.objects.create(
#     text="What is the capital of France?",
#     choices={"A": "Berlin", "B": "Madrid", "C": "Paris", "D": "Rome"},
#     correct_answer="C",
#     difficulty=2
# )

# Querying all questions
#for label, choice_text in q.choices.items():
    # print(f"{label}: {choice_text}")


class TestSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    lexile = models.IntegerField(null=True, blank=True)
    age = models.IntegerField()
    grade = models.CharField(max_length=10)
    hours = models.FloatField()
    is_esl = models.BooleanField()

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    current_theta = models.FloatField(default=0.0)
    current_question = models.ForeignKey(
        QuestionBank, on_delete=models.SET_NULL, null=True, blank=True
    )
    answered_questions = models.JSONField(default=list) # Store as [question_id, is_correct]

    def __str__(self):
        return f"Theta: {self.current_theta}; Question: {self.current_question}"

    
    def estimate_initial_theta(self):
        """Estimate an initial theta value based on user attributes."""
        BASE_THETA = {'K-1': -1.2, '2-3': -0.8, '4-5': -0.4, '6-8': 0.0, 
                    '9-10': 0.5, '11-12': 1.0, 'college': 1.5, 'none': 1.5}
        
        # Base theta from grade level
        theta = BASE_THETA.get(self.grade, 0.0)  

        # Adjust for age, but limit extreme influence
        theta += min(max((self.age - 10) * 0.2, -1), 1)  # Limit between -1 and 1

        # Adjust for study hours
        if self.hours >= 3:
            theta += 0.3
        elif self.hours >= 1:
            theta += 0.0
        else:
            theta -= 0.3

        # Adjust for ESL status with a smaller penalty
        if self.is_esl:
            theta -= 0.2  # Instead of -0.3, so it's less extreme

        # Normalize Lexile score, but reduce its impact
        if self.lexile:
            lexile_adj = (self.lexile - 850) / 400  # Reduced impact
            theta += min(max(lexile_adj, -1), 1)  # Keep within [-1, 1]

        # Final bounding to ensure theta is reasonable
        theta = min(max(theta, -3.0), 3.0)

        print("Initial theta is:", round(theta, 2))
        return round(theta, 2)
    
    def add_question(self, question_id, is_correct):
        answered = self.answered_questions  # Retrieve current list
        answered.append({"question_id": question_id, "is_correct": is_correct})  # Append new entry
        self.answered_questions = answered  # Update field
        self.save()

    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only estimate on creation
            self.current_theta = self.estimate_initial_theta()
        super().save(*args, **kwargs)

    def get_administered(self):
        answered_ids = []
        is_correct = []
        # subtract 1 from question id because lists 0 index
        for entry in self.answered_questions:
            answered_ids.append(entry['question_id'] - 1)
            is_correct.append(entry["is_correct"])

        # print("Answered IDs", answered_ids)
        # print("Correctness", is_correct)
        return answered_ids, is_correct