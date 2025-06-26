from datetime import datetime
from django.db import models
from django.db.models import Avg, Count, Sum
from django.contrib.auth.models import User
from django.utils import timezone
import numpy as np
import statistics

# Create your models here.
class QuestionBank(models.Model):
    text = models.TextField()
    choices = models.JSONField()  # stores options as a dict
    correct_answer = models.CharField(max_length=2)  # 'A', 'B', 'C', etc.
    # antonym = models.CharField(max_length=2, null=True, blank=True)
    # unrelated = models.CharField(max_length=2, null=True, blank=True)
    QUESTION_TYPES = (('syn', 'Synonym'), ('wic', 'Word In Context'))
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

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
    language = models.BooleanField()

    start_time = models.DateTimeField(null=True, blank=True)
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
        if self.language:
            theta -= 0.2  # Instead of -0.3, so it's less extreme

        # Normalize Lexile score, but reduce its impact
        if self.lexile:
            lexile_adj = (self.lexile - 850) / 400  # Reduced impact
            theta += min(max(lexile_adj, -1), 1)  # Keep within [-1, 1]

        # Final bounding to ensure theta is reasonable
        theta = min(max(theta, -3.0), 3.0)

        print("Initial theta is:", round(theta, 2))
        return round(theta, 2)
    
    def add_question(self, question_id, is_correct, user_answer, answered_time):
        answered = self.answered_questions  # Retrieve current list
        answered.append({"question_id": question_id, 
                         "is_correct": is_correct, 
                         "user_answer": user_answer,
                         "answered_time": answered_time.isoformat()})  # Append new entry
        print(answered)
        # self.answered_questions = answered  # Update field
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
            answered_ids.append(entry['question_id'])
            is_correct.append(entry["is_correct"])

        # print("Answered IDs", answered_ids)
        # print("Correctness", is_correct)
        return answered_ids, is_correct
    
    def get_details(self):
        """Get detailed stats for each question in this session"""
        stats = []  # [question_obj, is_correct, user_answer, time_to_answer, question_type]
        
        if not self.answered_questions:
            return stats
        
        for i, question_data in enumerate(self.answered_questions):
            # Parse the answered_time from ISO format
            answered_time = datetime.fromisoformat(question_data["answered_time"])
            if answered_time.tzinfo is None:
                answered_time = timezone.make_aware(answered_time)
            
            # Calculate time to answer this question
            if i == 0:
                # First question: time from start to answer
                time_to_answer = (answered_time - self.start_time).total_seconds()
            else:
                # Subsequent questions: time from previous answer to this answer
                prev_answered_time = datetime.fromisoformat(self.answered_questions[i-1]["answered_time"])
                if prev_answered_time.tzinfo is None:
                    prev_answered_time = timezone.make_aware(prev_answered_time)
                time_to_answer = (answered_time - prev_answered_time).total_seconds()
            
            # Get question object
            question = QuestionBank.objects.get(id=question_data['question_id'])
            
            stats.append({
                'question_id': question.id,
                'question_text': question.text, 
                'question_correct': question_data["is_correct"], 
                'user_answer': question.choices[question_data["user_answer"]] if question_data["user_answer"] else "None", 
                'correct_answer': question.choices[question.correct_answer],
                'time_to_answer': round(time_to_answer, 3),
                'question_type': question.question_type
            })
        
        return stats
    
    def get_stats(self):
        """Calculate comprehensive statistics for this session"""
        details = self.get_details()
        if not details:
            return {
                'total_questions': 0,
                'percent_correct': 0,
                'avg_time_per_question': 0,
                'avg_time_syn': 0,
                'avg_time_wic': 0,
                'total_syn_questions': 0,
                'total_wic_questions': 0,
                'syn_correct': 0,
                'wic_correct': 0,
                'syn_percent_correct': 0,
                'wic_percent_correct': 0,
                'total_time': 0,
                'syn_missed': 0,
                'wic_missed': 0,
                'syn_incorrect': 0,
                'wic_incorrect': 0,
            }
        # Basic stats
        total_questions = len(details)
        correct_answers = sum(1 for x in details if x['question_correct'])  # x[1] is is_correct
        percent_correct = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Time stats
        times = [x['time_to_answer'] for x in details]  # x[3] is time_to_answer
        assert(times)
        avg_time_per_question = statistics.mean(times) if times else 0
        total_time = sum(times)
        fastest_question = min(times) if times else 0
        slowest_question = max(times) if times else 0
        
        # Question type specific stats
        syn_questions = [x for x in details if x['question_type'] == 'syn']  # x[4] is question_type
        wic_questions = [x for x in details if x['question_type'] == 'wic']
        
        # SYN stats
        total_syn_questions = len(syn_questions)
        syn_times = [x['time_to_answer'] for x in syn_questions]
        avg_time_syn = statistics.mean(syn_times) if syn_times else 0
        syn_correct = sum(1 for x in syn_questions if x['question_correct'])
        syn_missed = 0
        # syn_percent_correct = (syn_correct / total_syn_questions * 100) if total_syn_questions > 0 else 0
        
        # WIC stats
        total_wic_questions = len(wic_questions)
        wic_times = [x['time_to_answer'] for x in wic_questions]
        avg_time_wic = statistics.mean(wic_times) if wic_times else 0
        wic_correct = sum(1 for x in wic_questions if x['question_correct'])
        wic_missed = 0
        # wic_percent_correct = (wic_correct / total_wic_questions * 100) if total_wic_questions > 0 else 0
        
        return {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'percent_correct': round(percent_correct, 2),
            'avg_time_per_question': round(avg_time_per_question, 2),
            'avg_time_syn': round(avg_time_syn, 2),
            'avg_time_wic': round(avg_time_wic, 2),
            'total_syn_questions': total_syn_questions,
            'total_wic_questions': total_wic_questions,
            'syn_correct': syn_correct,
            'wic_correct': wic_correct,
            'syn_missed': syn_missed,
            'wic_missed': wic_missed,
            'syn_incorrect': total_syn_questions - (syn_correct + syn_missed),
            'wic_incorrect': total_wic_questions - (wic_correct + wic_missed),
            'total_time': round(total_time, 2),
        }