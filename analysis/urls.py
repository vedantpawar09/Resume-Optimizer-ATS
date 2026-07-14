from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('confirm/<int:resume_id>/<int:jd_id>/', views.confirm_analysis, name='confirm'),
    path('run/<int:resume_id>/<int:jd_id>/', views.run_analysis, name='run_analysis'),
    path('confirm-skills/<int:analysis_id>/', views.confirm_missing_skills, name='confirm_missing_skills'),
    path('results/<int:analysis_id>/', views.results, name='results'),
    path('compare/<int:analysis_id>/', views.compare, name='compare'),
    path('download/<int:analysis_id>/<str:file_format>/', views.download, name='download'),
]
