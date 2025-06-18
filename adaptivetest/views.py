from django.db.models import Avg, Count, Sum
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from .models import QuestionBank, TestSession
from .forms import TestSessionForm
from .irt_logic import IRTModel
import statistics

# ------------------------
# Static pages (Home, Start)
# ------------------------

def home(request):
    return render(request, 'home.html')


def start_test(request):
    if request.method == "GET":
        context = {
            'form': TestSessionForm(),
            'message': "Please answer the following questions."
        }
        return render(request, 'adaptivetest/test.html', context)

    form = TestSessionForm(request.POST)
    if not form.is_valid():
        error_messages = form.errors.as_text()
        context = {'form': form, 'message': f'Invalid response: {error_messages}'}
        return render(request, 'test.html', context)

    age = form.cleaned_data['age']
    grade = form.cleaned_data['grade']
    hours = form.cleaned_data['hours']
    language = form.cleaned_data['language']
    lexile = form.cleaned_data.get('lexile')

    newTestSession = TestSession(age=age, grade=grade, hours=hours, language=language, lexile=lexile)
    newTestSession.save()

    model = IRTModel()
    starting_question = model.get_next_question(newTestSession)
    newTestSession.current_question = starting_question
    newTestSession.save()

    print("CURRENT ID", newTestSession.id)
    print("Started successfully.  First question: ", starting_question)

    # Redirect to intro slide sequence
    return redirect('brick1', session_id=newTestSession.id)


# ------------------------
# Intro + Tutorial Slide Flow
# ------------------------

def brick_welcomes_players1(request, session_id):
    return render(request, 'adaptivetest/brick_welcomes_players1.html', {
        'redirect_url': reverse('brick2', args=[session_id])
    })

def brick_welcomes_players2(request, session_id):
    return render(request, 'adaptivetest/brick_welcomes_players2.html', {
        'redirect_url': reverse('tutorial1', args=[session_id])
    })

def tutorial1(request, session_id):
    return render(request, 'adaptivetest/tutorial1.html', {
        'redirect_url': reverse('tutorial2', args=[session_id])
    })

def tutorial2(request, session_id):
    return render(request, 'adaptivetest/tutorial2.html', {
        'redirect_url': reverse('tutorial3', args=[session_id])
    })

def tutorial3(request, session_id):
    return render(request, 'adaptivetest/tutorial3.html', {
        'redirect_url': reverse('get_ready', args=[session_id])
    })

def get_ready(request, session_id):
    return render(request, 'adaptivetest/get_ready.html', {
        'redirect_url': reverse('game_countdown', args=[session_id])
    })


# ------------------------
# Countdown & Question Flow
# ------------------------

def game_countdown(request, session_id):
    redirect_url = reverse('question', args=[session_id])
    return render(request, 'adaptivetest/countdown.html', {
        'redirect_url': redirect_url
    })


def question_view(request, session_id):
    """Display current question and handle responses"""
    session = TestSession.objects.get(id=session_id)

    if request.method == 'POST':
        question_id = session.current_question.id
        print("QUESTION ID", question_id)
        user_answer = request.POST.get('answer')

        model = IRTModel()
        question = QuestionBank.objects.get(id=question_id)
        is_correct = (user_answer == question.correct_answer)

        session.add_question(question_id, is_correct, user_answer, timezone.now())
        model.update_theta(session)

        next_question = model.get_next_question(session)

        if next_question and not model.stop_test(session):
            session.current_question = next_question
            session.save()

            is_last = model.stop_test(session)  # Check if the next one is the last
            print(f"---------Question number {len(session.get_administered()[0])}.  Is last? {is_last} -------")
            return render(request, 'question.html', {
                'session_id': session.id,
                'question': next_question,
                'is_last': is_last
            })
        else:
            if session.end_time:
                return redirect('results', session_id=session.id)
            else:
                session.end_time = timezone.now()
                session.save()
                return render(request, 'question.html', {
                    'session_id': session.id,
                    'is_last': is_last
                    })
            

    # GET request
    model = IRTModel()
    is_last = model.stop_test(session)

    return render(request, 'question.html', {
        'session_id': session.id,
        'question': session.current_question,
        'is_last': is_last
    })


# ------------------------
# Results
# ------------------------

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

# In template
def view_stats(request):
    """Display comprehensive statistics for all sessions"""
    all_sessions = TestSession.objects.all().order_by('-start_time')
    session_stats = []
    
    # Collect stats for each session
    for session in all_sessions:
        stats = session.get_stats()
        session_info = {
            'session': session,
            'stats': stats,
            'user': session.user,
            'start_time': session.start_time,
            'grade': session.grade,
            'age': session.age,
        }
        session_stats.append(session_info)
    
    # Calculate overall aggregate statistics
    if session_stats:
        # Overall performance stats
        all_stats = [s['stats'] for s in session_stats if s['stats']['total_questions'] > 0]
        
        if all_stats:
            # Average statistics across all sessions
            overall_stats = {
                'total_sessions': len(all_stats),
                'avg_questions_per_session': round(statistics.mean([s['total_questions'] for s in all_stats]), 1),
                'avg_accuracy': round(statistics.mean([s['percent_correct'] for s in all_stats]), 1),
                'avg_time_per_question': round(statistics.mean([s['avg_time_per_question'] for s in all_stats]), 2),
                'avg_time_syn': round(statistics.mean([s['avg_time_syn'] for s in all_stats if s['avg_time_syn'] > 0]), 2),
                'avg_time_wic': round(statistics.mean([s['avg_time_wic'] for s in all_stats if s['avg_time_wic'] > 0]), 2),
                'total_questions_answered': sum([s['total_questions'] for s in all_stats]),
                'total_syn_questions': sum([s['total_syn_questions'] for s in all_stats]),
                'total_wic_questions': sum([s['total_wic_questions'] for s in all_stats]),
                # 'syn_accuracy': round(statistics.mean([s['syn_percent_correct'] for s in all_stats if s['syn_percent_correct'] > 0]), 1),
                # 'wic_accuracy': round(statistics.mean([s['wic_percent_correct'] for s in all_stats if s['wic_percent_correct'] > 0]), 1),
            }
            
            # Grade-based statistics
            grade_stats = {}
            for session_info in session_stats:
                grade = session_info['grade']
                if grade not in grade_stats:
                    grade_stats[grade] = []
                if session_info['stats']['total_questions'] > 0:
                    grade_stats[grade].append(session_info['stats'])
            
            # Calculate averages per grade
            grade_averages = {}
            for grade, stats_list in grade_stats.items():
                if stats_list:
                    grade_averages[grade] = {
                        'count': len(stats_list),
                        'avg_accuracy': round(statistics.mean([s['percent_correct'] for s in stats_list]), 1),
                        'avg_time': round(statistics.mean([s['avg_time_per_question'] for s in stats_list]), 2),
                        'avg_questions': round(statistics.mean([s['total_questions'] for s in stats_list]), 1),
                    }
        else:
            overall_stats = {}
            grade_averages = {}
    else:
        overall_stats = {}
        grade_averages = {}
    
    context = {
        'session_stats': session_stats,
        'overall_stats': overall_stats,
        'grade_averages': grade_averages,
        'has_data': len(session_stats) > 0,
    }
    
    return render(request, 'stats.html', context)