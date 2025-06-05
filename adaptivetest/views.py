from django.shortcuts import render, redirect
from .models import QuestionBank, TestSession
from .forms import TestSessionForm
from .irt_logic import IRTModel
from django.utils import timezone

def home(request):
    return render(request, 'home.html')

def start_test(request):
    if request.method == "GET":
        context = {
            'form': TestSessionForm(),
            'message': "In order to best assess your current vocabulary level, please answer the following questions"
        }
        return render(request, 'test.html', context)

    form = TestSessionForm(request.POST)
    if not form.is_valid():
        context = {'form': form, 'message': 'Invalid response. Please try again'}
        return render(request, 'test.html', context)

    age = form.cleaned_data['age']
    grade = form.cleaned_data['grade']
    hours = form.cleaned_data['hours']
    language = form.cleaned_data['language']
    lexile = form.cleaned_data.get('lexile')

    newTestSession = TestSession(age=age, grade=grade, hours=hours, is_esl=language, lexile=lexile)
    newTestSession.save()

    model = IRTModel()
    starting_question = model.get_next_question(newTestSession)
    newTestSession.current_question = starting_question
    newTestSession.save()

    print("CURRENT ID", newTestSession.id)
    print(starting_question)

    # Check if the first question is also the last one
    is_last = model.stop_test(newTestSession)

    return render(request, 'question.html', {
        'session_id': newTestSession.id,
        'question': starting_question,
        'is_last': is_last
    })

def question_view(request, session_id):
    """Display current question and handle responses"""
    session = TestSession.objects.get(id=session_id)

    if request.method == 'POST':
        question_id = session.current_question.id
        user_answer = request.POST.get('answer')

        model = IRTModel()
        question = QuestionBank.objects.get(id=question_id)
        is_correct = (user_answer == question.correct_answer)

        session.add_question(question_id, is_correct)
        model.update_theta(session)

        next_question = model.get_next_question(session)

        if next_question and not model.stop_test(session):
            session.current_question = next_question
            session.save()

            is_last = model.stop_test(session)  # Check if the next one is the last
            return render(request, 'question.html', {
                'session_id': session.id,
                'question': next_question,
                'is_last': is_last
            })
        else:
            session.end_time = timezone.now()
            session.save()
            return redirect('results', session_id=session.id)

    # GET request
    model = IRTModel()
    is_last = model.stop_test(session)

    return render(request, 'question.html', {
        'session_id': session.id,
        'question': session.current_question,
        'is_last': is_last
    })

def test_results(request, session_id):
    """Display test results"""
    session = TestSession.objects.get(id=session_id)
    total_questions = len(session.get_administered()[0])
    for_catboost = [
        f"Question {ind}: Correct" if correct else f"Question {ind}: Incorrect"
        for ind, correct in zip(session.get_administered()[0], session.get_administered()[1])
    ]
    correct_answers = sum(1 for correct in session.get_administered()[1] if correct)

    return render(request, 'results.html', {
        'session': session,
        'total_questions': total_questions,
        'catboost': for_catboost[::-1]
    })
