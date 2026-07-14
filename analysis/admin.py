from django.contrib import admin
from .models import ATSAnalysis, ResumeHistory


@admin.register(ATSAnalysis)
class ATSAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'resume', 'ats_score_before', 'ats_score_after', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'resume__original_filename')


@admin.register(ResumeHistory)
class ResumeHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'note', 'created_at')
    list_filter = ('action', 'created_at')
