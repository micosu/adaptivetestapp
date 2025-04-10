import numpy as np
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
# from catsim.irt import ThreePLModel
from catsim.stopping import MaxItemStopper, MinErrorStopper
from .models import TestSession, QuestionBank 

items = True
class IRTModel:
    # Get all questions and format for catsim
    # CHECK
    all_questions = list(QuestionBank.objects.all().values("id", "discrimination", "difficulty", "guessing"))
    
    # Convert to NumPy array: [discrimination, difficulty, guessing]
    item_bank = np.array([[q["discrimination"], q["difficulty"], q["guessing"], 1] for q in all_questions])

    def __init__(self):
        self.selector = MaxInfoSelector()  # Selects best next question
        self.estimator = NumericalSearchEstimator()  # Updates theta
        # self.model = ThreePLModel()  # 3PL Model (can be changed to 2PL or 1PL)
        self.stop_items = MaxItemStopper(5)
        self.stop_error = MinErrorStopper(.3)

    def update_theta(self, test_session):
        """Update the test-taker's theta based on their response to the question."""
        # item_params = np.array([question.discrimination, question.difficulty, question.guessing])
        administered, responses = test_session.get_administered()

        initial_t = test_session.current_theta
        test_session.current_theta = self.estimator.estimate(items=IRTModel.item_bank, 
                                                             administered_items=administered, 
                                                             response_vector=responses,
                                                             est_theta=test_session.current_theta)
        
        print(f"The most recent was {'Correct' if responses[-1] else 'Incorrect'}")
        print(f"So theta changed from {initial_t} to {test_session.current_theta}")
        test_session.save()
    
    def get_next_question(self, test_session):
        """Select the next best question based on the user's current ability (theta)."""
        
        # Get the indexes of already answered questions
        # shift by to account for 0 indexing since item_bank will start at 0
        administered = test_session.get_administered()[0]
        available_items = [i for i, q in enumerate(IRTModel.all_questions) if q["id"] not in administered]

        if not available_items:
            return None  # No more questions available

        # Select the next question
        # item_index = selector.select(items=items, administered_items=administered_items, est_theta=est_theta)
        print("Administered:", administered)
        next_index = self.selector.select(items=IRTModel.item_bank, administered_items=administered, est_theta=test_session.current_theta)
        next_question_id = IRTModel.all_questions[next_index]["id"]
        return QuestionBank.objects.get(id=next_question_id)

    

    def stop_test(self, test_session):
        administered = test_session.get_administered()[0]
        est_theta = test_session.current_theta

        if items:
            return self.stop_items.stop(administered_items=self.item_bank[administered])
        else:
            return self.stop_error.stop(administered_items=self.item_bank[administered], theta=est_theta)
