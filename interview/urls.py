from django.urls import path
from . import views

app_name = 'interview'

urlpatterns = [
    path('generate/<int:analysis_id>/', views.generate_questions, name='generate_questions'),
    path('mock/<int:qset_id>/', views.mock_interview, name='mock_interview'),
    path('mock/<int:session_id>/answer/', views.submit_mock_answer, name='submit_mock_answer'),
    path('mock/<int:session_id>/complete/', views.complete_mock_session, name='complete_mock_session'),
]
