from django.shortcuts import render, redirect
from .models import QuestionBank, TestSession
from .forms import TestSessionForm
from .irt_logic import IRTModel
from django.utils import timezone

def home(request):
    return render(request, 'home.html')
    
def start_test(request):
    if request.method == "GET":
        context = {'form': TestSessionForm(), 'message': "In order to best assess your current vocabulary level, please answer the following questions"}
        return render(request, 'test.html', context)
    
    form = TestSessionForm(request.POST)
    if not form.is_valid():
        context = {'form': form, 'message': 'Invalid response.  Please try again'}
        return render(request, 'test.html', context)
    
    
    age = form.cleaned_data['age']
    grade = form.cleaned_data['grade']
    hours = form.cleaned_data['hours']
    language = form.cleaned_data['language']
    lexile = form.cleaned_data.get('lexile')

    newTestSession = TestSession(age = age, grade=grade, hours=hours, is_esl=language, lexile=lexile)
    newTestSession.save()

    model = IRTModel()
    starting_question = model.get_next_question(newTestSession)
    newTestSession.current_question = starting_question
    newTestSession.save()
    print("CURRENT ID", newTestSession.id)
    print(starting_question)
    # return redirect('question', session_id=newTestSession.id)
    return render(request, 'question.html', {'session_id': newTestSession.id, 'question': starting_question})


# @login_required
def question_view(request, session_id):
    """Display current question and handle responses"""
    session = TestSession.objects.get(id=session_id)
    
    if request.method == 'POST':
        # Process answer
        question_id = session.current_question.id
        print(question_id)
        user_answer = request.POST.get('answer')

        model = IRTModel()
        print("User answer", user_answer)
        # Get correct answer
        question = QuestionBank.objects.get(id=question_id)
        print("Is correct?", user_answer == question.correct_answer)
        is_correct = (user_answer == question.correct_answer)
        
        # Update ability estimate
        session.add_question(question_id, is_correct)
        model.update_theta(session)
        
        # Get next question
        next_question = model.get_next_question(session)
        
        if next_question and not model.stop_test(session):
            # Continue test
            session.current_question = next_question
            session.save()
            return render(request, 'question.html', {
                'session_id': session.id,
                'question': next_question
            })
        else:
            # End test
            session.end_time = timezone.now()
            session.save()
            return redirect('results', session_id=session.id)
    
    # GET request: Display current question
    return render(request, 'question.html', {
        'session_id': session.id,
        'question': session.current_question
    })


def test_results(request, session_id):
    """Display test results"""
    session = TestSession.objects.get(id=session_id)
    
    # Calculate results
    total_questions = len(session.get_administered()[0])
    correct_answers = sum(1 for correct in session.get_administered()[1] if correct)
    
    return render(request, 'results.html', {
        'session': session,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'final_ability': round(session.current_theta, 2)
    })