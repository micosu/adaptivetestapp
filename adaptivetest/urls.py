from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("test", views.start_test, name="test"),
    path("question/<int:session_id>", views.question_view, name="question"),
    path('results/<int:session_id>', views.test_results, name="results")
]