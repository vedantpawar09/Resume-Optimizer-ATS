from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('upload/', views.upload_resume, name='upload_resume'),
    path('job-description/', views.add_job_description, name='add_job_description'),
    path('preview/<int:resume_id>/', views.resume_preview, name='resume_preview'),
]
