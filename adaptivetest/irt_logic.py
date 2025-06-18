import numpy as np
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
from catsim.stopping import MaxItemStopper, MinErrorStopper
from .models import QuestionBank 
import os
import django

stopping_method = "time"

class IRTModel:
    # Get all questions and format for catsim
    # if os.environ.get('DJANGO_SETTINGS_MODULE') and django.apps.apps.ready:
    #     try:
    #         from adaptivetest.models import QuestionBank
    #         all_questions = list(QuestionBank.objects.all().values("id", "discrimination", "difficulty", "guessing", "question_type"))
    #     except:
    #         all_questions = []  # Fallback when table doesn't exist
    # else:
    #     all_questions = []
    
    # # Separate questions by type
    # syn_questions = [q for q in all_questions if q["question_type"] == "syn"]
    # wic_questions = [q for q in all_questions if q["question_type"] == "wic"]
    
    # # Convert to NumPy arrays: [discrimination, difficulty, guessing, asymptote]
    # syn_item_bank = np.array([[q["discrimination"], q["difficulty"], q["guessing"], 1] for q in syn_questions])
    # wic_item_bank = np.array([[q["discrimination"], q["difficulty"], q["guessing"], 1] for q in wic_questions])
    
    def __init__(self):
        self.selector = MaxInfoSelector()  # Selects best next question
        self.estimator = NumericalSearchEstimator()  # Updates theta
        self.stop_items = MaxItemStopper(90)
        self.stop_error = MinErrorStopper(.3)

        # Load and cache items when initialized
        self._load_item_banks()

    def _load_item_banks(self):
        from adaptivetest.models import QuestionBank
        self.all_questions = list(QuestionBank.objects.all().values("id", "discrimination", "difficulty", "guessing", "question_type"))

        self.syn_questions = [q for q in self.all_questions if q["question_type"] == "syn"]
        self.wic_questions = [q for q in self.all_questions if q["question_type"] == "wic"]

        self.syn_item_bank = np.array([[q["discrimination"], q["difficulty"], q["guessing"], 1] for q in self.syn_questions])
        self.wic_item_bank = np.array([[q["discrimination"], q["difficulty"], q["guessing"], 1] for q in self.wic_questions])
    
    def _get_current_question_type(self, test_session):
        """Determine what type of question should be asked next based on the pattern."""
        administered_ids, _ = test_session.get_administered()
        
        # Count questions by type that have been administered
        syn_count = 0
        wic_count = 0
        
        for q_id in administered_ids:
            # Find the question type for this ID
            for q in self.all_questions:
                if q["id"] == q_id:
                    if q["question_type"] == "syn":
                        syn_count += 1
                    elif q["question_type"] == "wic":
                        wic_count += 1
                    break
        
        # Determine pattern position
        total_administered = len(administered_ids)
        position_in_cycle = total_administered % 6  # 5 syn + 1 wic = 6 question cycle
        
        # First 5 positions (0-4) should be syn, 6th position (5) should be wic
        if position_in_cycle < 5:
            return "syn"
        else:
            return "wic"
    
    def _get_administered_by_type(self, test_session, question_type):
        """Get administered question indices for a specific question type."""
        administered_ids, responses = test_session.get_administered()
        
        # Get the question list for the specified type
        question_list = self.syn_questions if question_type == "syn" else self.wic_questions
        
        # Find indices and responses for this question type
        type_administered = []
        type_responses = []
        
        for i, q_id in enumerate(administered_ids):
            # Check if this question ID belongs to the current type
            for j, q in enumerate(question_list):
                if q["id"] == q_id:
                    type_administered.append(j)  # Index in the type-specific list
                    type_responses.append(responses[i])
                    break
        
        return type_administered, type_responses
    
    def update_theta(self, test_session):
        """Update the test-taker's theta based on their response to the question."""
        administered_ids, all_responses = test_session.get_administered()
        
        if not administered_ids:
            return
        
        # Get the type of the most recent question
        last_question_id = administered_ids[-1]
        last_question_type = None
        
        for q in self.all_questions:
            if q["id"] == last_question_id:
                last_question_type = q["question_type"]
                break
        
        if not last_question_type:
            print(f"Warning: Could not find question type for ID {last_question_id}")
            return
        
        # Get administered items and responses for this question type
        type_administered, type_responses = self._get_administered_by_type(test_session, last_question_type)
        
        if not type_administered:
            print(f"Warning: No administered items found for type {last_question_type}")
            return
        
        # Select the appropriate item bank
        item_bank = self.syn_item_bank if last_question_type == "syn" else self.wic_item_bank
        
        initial_theta = test_session.current_theta
        
        # Update theta using only questions of the same type
        test_session.current_theta = self.estimator.estimate(
            items=item_bank,
            administered_items=type_administered,
            response_vector=type_responses,
            est_theta=test_session.current_theta
        )
        
        print(f"Question type: {last_question_type}")
        print(f"The most recent was {'Correct' if all_responses[-1] else 'Incorrect'}")
        print(f"So theta changed from {initial_theta} to {test_session.current_theta}")
        test_session.save()
    
    def get_next_question(self, test_session):
        """Select the next best question based on the user's current ability and question type pattern."""
        
        # Determine what type of question should be asked next
        next_question_type = self._get_current_question_type(test_session)
        
        # Get administered items for this question type
        type_administered, _ = self._get_administered_by_type(test_session, next_question_type)
        
        # Select the appropriate question list and item bank
        if next_question_type == "syn":
            question_list = self.syn_questions
            item_bank = self.syn_item_bank
        else:
            question_list = self.wic_questions
            item_bank = self.wic_item_bank
        
        # Check if there are available questions of this type
        available_items = [i for i in range(len(question_list)) if i not in type_administered]
        
        if not available_items:
            print(f"No more {next_question_type} questions available")
            return None
        
        # Select the next question using CAT algorithm
        print(f"Next question type: {next_question_type}")
        print(f"Administered {next_question_type} items:", type_administered)
        
        next_index = self.selector.select(
            items=item_bank,
            administered_items=type_administered,
            est_theta=test_session.current_theta
        )
        
        next_question_id = question_list[next_index]["id"]
        return QuestionBank.objects.get(id=next_question_id)
    
    def stop_test(self, test_session, time_remaining=None):
        """Determine if the test should stop based on stopping criteria."""
        administered_ids, _ = test_session.get_administered()
        
        # Get administered items from both question types
        syn_administered, _ = self._get_administered_by_type(test_session, "syn")
        wic_administered, _ = self._get_administered_by_type(test_session, "wic")
        
        # Create combined administered items array with item parameters
        combined_administered_items = []
        
        # Add syn items
        if syn_administered:
            syn_items = self.syn_item_bank[syn_administered]
            combined_administered_items.extend(syn_items)
        
        # Add wic items  
        if wic_administered:
            wic_items = self.wic_item_bank[wic_administered]
            combined_administered_items.extend(wic_items)
        
        if not combined_administered_items:
            return False  # No items administered yet
        
        # Convert to numpy array
        administered_items_array = np.array(combined_administered_items)
        
        if stopping_method == "item":
            return self.stop_items.stop(administered_items=administered_items_array)
        elif stopping_method == "time":
            if time_remaining is not None and time_remaining <= 0:
                return True
            else:
                return False
        else:
            return self.stop_error.stop(administered_items=administered_items_array, theta=test_session.current_theta)