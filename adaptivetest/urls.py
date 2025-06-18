from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # Test form and session creation
    path('start/', views.start_test, name='start_test'),
    path('test/', views.start_test, name='start_test'),  # optional alias

    # Intro sequence
    path('brick1/<int:session_id>/', views.brick_welcomes_players1, name='brick1'),
    path('brick2/<int:session_id>/', views.brick_welcomes_players2, name='brick2'),
    path('tutorial1/<int:session_id>/', views.tutorial1, name='tutorial1'),
    path('tutorial2/<int:session_id>/', views.tutorial2, name='tutorial2'),
    path('tutorial3/<int:session_id>/', views.tutorial3, name='tutorial3'),
    path('get_ready/<int:session_id>/', views.get_ready, name='get_ready'),

    # Countdown and test
    path('quiz/set-start-time/<int:session_id>/', views.set_start_time, name="start_time"),
    path('countdown/<int:session_id>/', views.game_countdown, name='game_countdown'),
    path('question/<int:session_id>/', views.question_view, name='question'),
    path('results/<int:session_id>/', views.test_results, name='results'),

    # Stats
    path('stats', views.view_stats, name="stats")
]
