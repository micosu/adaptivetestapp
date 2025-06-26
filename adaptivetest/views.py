from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from .models import QuestionBank, TestSession
from .forms import TestSessionForm
from .irt_logic import IRTModel
import statistics
import json

# ------------------------
# Static pages (Home, Start)
# ------------------------

def home(request):
    return render(request, 'home.html')


def start_test(request):
    if request.method == "GET":
        return render(request, 'adaptivetest/test.html', {
            'form': TestSessionForm(),
            'message': "Please answer the following questions."
        })

    form = TestSessionForm(request.POST)
    if not form.is_valid():
        return render(request, 'test.html', {
            'form': form,
            'message': f"Invalid response: {form.errors.as_text()}"
        })

    data = form.cleaned_data
    session = TestSession(**data)
    session.save()

    model = IRTModel()
    first_question = model.get_next_question(session)
    session.current_question = first_question
    session.save()

    return redirect('brick1', session_id=session.id)


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
    return render(request, 'adaptivetest/countdown.html', {
        'redirect_url': reverse('question', args=[session_id])
    })

def set_start_time(request, session_id):
    if request.method == 'POST':
        session = TestSession.objects.get(id=session_id)
        data = json.loads(request.body)
        start_time_ms = data.get('quizStartTime')
        if start_time_ms:
            session.start_time = timezone.datetime.fromtimestamp(
                start_time_ms / 1000, tz=timezone.get_current_timezone()
            )
            session.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})


def question_view(request, session_id):
    session = TestSession.objects.get(id=session_id)

    if request.method == 'POST':
        question_id = session.current_question.id
        user_answer = request.POST.get('answer')
        time_limit = int(request.POST.get('time_limit'))

        # Check remaining time
        if session.start_time:
            elapsed = (timezone.now() - session.start_time).total_seconds() * 1000
            time_remaining = time_limit - elapsed
        else:
            time_remaining = time_limit

        # Handle timing and answers as before...
        model = IRTModel()
        question = QuestionBank.objects.get(id=question_id)
        is_correct = (user_answer == question.correct_answer)
        
        # Your existing timestamp handling...
        start_time = int(request.POST.get('start_time'))
        start_time = timezone.datetime.fromtimestamp(start_time / 1000, tz=timezone.get_current_timezone())
        submit_time = int(request.POST.get('submit_time'))
        submit_time = timezone.datetime.fromtimestamp(submit_time / 1000, tz=timezone.get_current_timezone())
        question_duration_seconds = (submit_time - start_time).total_seconds()

        if time_remaining <= 0:
            session.end_time = timezone.now()
            session.save()
            # Return JSON for AJAX
            return JsonResponse({
                'expired': True, 
                'redirect_url': f'/results/{session.id}'
            })
        
        session.add_question(question_id, is_correct, user_answer, question_duration_seconds)
        model.update_theta(session)

        next_q = model.get_next_question(session)
        if next_q:
            session.current_question = next_q
            session.save()
            # Return JSON with next question URL
            return JsonResponse({
                'expired': False,
                'redirect_url': f'/question/{session.id}/'
            })
        else:
            # No more questions
            session.end_time = timezone.now()
            session.save()
            return JsonResponse({
                'expired': False,
                'redirect_url': f'/results/{session.id}'
            })

    # GET request
    return render(request, 'question.html', {
        'session_id': session.id,
        'question': session.current_question,
    })

def check_session_status(request, session_id):
    session = TestSession.objects.get(id=session_id)
    time_limit = int(request.GET.get('time_limit'))
    if session.start_time:
        elapsed = (timezone.now() - session.start_time).total_seconds() * 1000
        time_remaining = time_limit - elapsed  # Your time limit in ms
        is_expired = time_remaining <= 0
    else:
        is_expired = False
    
    return JsonResponse({
        'expired': is_expired,
        'redirect_url': f'/results/{session.id}' if is_expired else None
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
        'correct_questions': correct_answers,
        'catboost': for_catboost[::-1]
    })

def get_stats(filtered=[]):
    """Display comprehensive statistics for all sessions"""
    if filtered:
        all_sessions = TestSession.objects.filter(id__in=filtered).order_by('-start_time')
    else:
        all_sessions = TestSession.objects.order_by('-start_time')
    session_stats = []
    
    # Collect stats for each session
    for session in all_sessions:
        stats = session.get_stats()
        session_info = {
            'session': session,
            'stats': stats,
            'user': session.user,
            'id': session.id,
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
            time_syn = [s['avg_time_syn'] for s in all_stats if s['avg_time_syn'] > 0]
            time_wic = [s['avg_time_wic'] for s in all_stats if s['avg_time_wic'] > 0]
            syn_counts = [s['total_syn_questions'] for s in all_stats if s['total_syn_questions'] > 0]
            wic_counts = [s['total_wic_questions'] for s in all_stats if s['total_wic_questions'] > 0]
            
            overall_stats = {
                'total_sessions': len(all_stats),
                # 'total_questions_answered': sum([s['total_questions'] for s in all_stats]),
                'avg_questions_per_session': round(statistics.mean([s['total_questions'] for s in all_stats]), 1),
                'avg_accuracy': round(statistics.mean([s['percent_correct'] for s in all_stats]), 1),
                'avg_time_per_question': round(statistics.mean([s['avg_time_per_question'] for s in all_stats]), 2),
                'avg_time_syn': round(statistics.mean(time_syn), 2) if time_syn else 0,
                'avg_time_wic': round(statistics.mean(time_wic), 2) if time_wic else 0,
                # 'total_syn_questions': sum([s['total_syn_questions'] for s in all_stats]),
                # 'total_wic_questions': sum([s['total_wic_questions'] for s in all_stats]),
                'avg_syn_per_session': round(statistics.mean(syn_counts), 1) if syn_counts else 0,
                'avg_wic_per_session': round(statistics.mean(wic_counts), 1) if wic_counts else 0,
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
    
    return context
# In template
def view_all_stats(request):
    context = get_stats()
    return render(request, 'stats.html', context)

def view_tester_stats(request):
    context = get_stats([26, 28, 34, 35, 36])
    return render(request, 'stats.html', context)

def view_individual_stats(request, session_id):
    session = TestSession.objects.get(id=session_id)
    session_info = get_stats([session_id])['session_stats'][0]
    details = session.get_details()
    return render(request, 'individual_stats.html', {'details': details, 'session_info': session_info})

