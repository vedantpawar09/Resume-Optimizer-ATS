from django.contrib import admin
from .models import Resume, JobDescription


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user', 'file_type', 'file_size_kb', 'uploaded_at')
    search_fields = ('original_filename', 'user__username')
    list_filter = ('file_type', 'uploaded_at')


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'user', 'created_at')
    search_fields = ('title', 'company', 'user__username')
