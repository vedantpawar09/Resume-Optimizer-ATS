import uuid
from django.db import models
from django.contrib.auth.models import User


def resume_upload_path(instance, filename):
    return f"resumes/{instance.user_id}/{uuid.uuid4().hex}_{filename}"


class Resume(models.Model):
    """An uploaded resume file plus its parsed plain-text content."""

    FILE_TYPES = (('pdf', 'PDF'), ('docx', 'DOCX'))

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to=resume_upload_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_size_kb = models.PositiveIntegerField(default=0)

    raw_text = models.TextField(blank=True, help_text="Full extracted plain text of the resume.")
    structured_sections = models.JSONField(
        default=dict, blank=True,
        help_text="Best-effort section split, e.g. {'summary': '...', 'experience': '...'}"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.user.username})"


class JobDescription(models.Model):
    """A job description, either pasted as text or uploaded as a PDF."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_descriptions')
    title = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    raw_text = models.TextField()
    source_file = models.FileField(upload_to='job_descriptions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"JD #{self.pk}"
