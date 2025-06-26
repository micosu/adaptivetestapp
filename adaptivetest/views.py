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

        # Check remaining time
        if session.start_time:
            elapsed = (timezone.now() - session.start_time).total_seconds() * 1000
            time_remaining = 2.3 * 60 * 1000 - elapsed
        else:
            time_remaining = 2.3 * 60 * 1000

        model = IRTModel()
        question = QuestionBank.objects.get(id=question_id)
        is_correct = (user_answer == question.correct_answer)

        session.add_question(question_id, is_correct, user_answer, timezone.now())
        model.update_theta(session)

        if time_remaining <= 0:
            session.end_time = timezone.now()
            session.save()
            return redirect('results', session_id=session.id)

        next_q = model.get_next_question(session)
        if next_q:
            session.current_question = next_q
            session.save()
            return render(request, 'question.html', {
                'session_id': session.id,
                'question': next_q,
            })

        session.end_time = timezone.now()
        session.save()
        return redirect('results', session_id=session.id)

    # GET request
    return render(request, 'question.html', {
        'session_id': session.id,
        'question': session.current_question,
    })


# ------------------------
# Results
# ------------------------

def test_results(request, session_id):
    session = TestSession.objects.get(id=session_id)
    question_ids, correctness = session.get_administered()
    catboost = [
        f"Question {qid}: {'Correct' if c else 'Incorrect'}"
        for qid, c in zip(question_ids, correctness)
    ][::-1]
    return render(request, 'results.html', {
        'session': session,
        'total_questions': len(question_ids),
        'catboost': catboost
    })


# ------------------------
# Stats Page
# ------------------------

def view_stats(request):
    sessions = TestSession.objects.all().order_by('-start_time')
    stats_all = []

    for s in sessions:
        stat = s.get_stats()
        stats_all.append({
            'session': s,
            'stats': stat,
            'user': s.user,
            'id': s.id,
            'start_time': s.start_time,
            'grade': s.grade,
            'age': s.age,
        })

    if not stats_all:
        return render(request, 'stats.html', {'has_data': False})

    valid_stats = [s['stats'] for s in stats_all if s['stats']['total_questions'] > 0]
    if not valid_stats:
        return render(request, 'stats.html', {'has_data': False})

    overall = {
        'total_sessions': len(valid_stats),
        'avg_questions_per_session': round(statistics.mean(s['total_questions'] for s in valid_stats), 1),
        'avg_accuracy': round(statistics.mean(s['percent_correct'] for s in valid_stats), 1),
        'avg_time_per_question': round(statistics.mean(s['avg_time_per_question'] for s in valid_stats), 2),
        'avg_time_syn': round(statistics.mean(s['avg_time_syn'] for s in valid_stats if s['avg_time_syn'] > 0), 2),
        'avg_time_wic': round(statistics.mean(s['avg_time_wic'] for s in valid_stats if s['avg_time_wic'] > 0), 2),
        'total_questions_answered': sum(s['total_questions'] for s in valid_stats),
        'total_syn_questions': sum(s['total_syn_questions'] for s in valid_stats),
        'total_wic_questions': sum(s['total_wic_questions'] for s in valid_stats),
    }

    by_grade = {}
    for s in stats_all:
        grade = s['grade']
        if grade not in by_grade:
            by_grade[grade] = []
        if s['stats']['total_questions'] > 0:
            by_grade[grade].append(s['stats'])

    grade_averages = {
        g: {
            'count': len(lst),
            'avg_accuracy': round(statistics.mean(s['percent_correct'] for s in lst), 1),
            'avg_time': round(statistics.mean(s['avg_time_per_question'] for s in lst), 2),
            'avg_questions': round(statistics.mean(s['total_questions'] for s in lst), 1),
        }
        for g, lst in by_grade.items() if lst
    }

    return render(request, 'stats.html', {
        'session_stats': stats_all,
        'overall_stats': overall,
        'grade_averages': grade_averages,
        'has_data': True,
    })
