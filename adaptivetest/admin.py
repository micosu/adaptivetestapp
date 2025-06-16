from django.contrib import admin
from .models import QuestionBank, TestSession

admin.site.register(QuestionBank)
admin.site.register(TestSession)