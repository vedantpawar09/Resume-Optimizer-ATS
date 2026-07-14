from django.contrib import admin
from .models import InterviewQuestionSet, MockInterviewSession, MockInterviewAnswer

admin.site.register(InterviewQuestionSet)
admin.site.register(MockInterviewSession)
admin.site.register(MockInterviewAnswer)
