from django.db import models
from django.contrib.auth.models import User

from resumes.models import Resume, JobDescription


class ATSAnalysis(models.Model):
    """Full AI + deterministic analysis of a Resume against a JobDescription."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analyses')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='analyses')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='analyses')

    ats_score_before = models.PositiveIntegerField(default=0)
    ats_score_after = models.PositiveIntegerField(default=0)
    keyword_match_percent = models.PositiveIntegerField(default=0)
    resume_match_percent = models.PositiveIntegerField(default=0)
    skills_match_percent = models.PositiveIntegerField(default=0)
    recruiter_match_percent = models.PositiveIntegerField(default=0)
    formatting_score = models.PositiveIntegerField(default=0)
    grammar_score = models.PositiveIntegerField(default=0)
    readability_score = models.PositiveIntegerField(default=0)

    matched_keywords = models.JSONField(default=list, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    suggested_keywords = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)

    weak_sections = models.JSONField(default=list, blank=True)
    strong_sections = models.JSONField(default=list, blank=True)
    section_analysis = models.JSONField(default=dict, blank=True)
    ats_formatting_checks = models.JSONField(default=dict, blank=True)
    overall_summary = models.TextField(blank=True)

    rewritten_sections = models.JSONField(default=dict, blank=True)
    change_log = models.JSONField(default=list, blank=True)
    keywords_inserted = models.JSONField(default=list, blank=True)
    fidelity_warnings = models.JSONField(
        default=list, blank=True,
        help_text="Facts (numbers, years, proper nouns) found in the original resume "
                   "that did not survive into the rewritten text - a safety net against "
                   "the AI silently dropping real accomplishments.",
    )
    user_approved_keywords = models.JSONField(
        default=list, blank=True,
        help_text="Missing keywords/skills the candidate explicitly confirmed they "
                   "have, before the rewrite step was allowed to add them.",
    )

    output_docx = models.FileField(upload_to='outputs/docx/', blank=True, null=True)
    output_pdf = models.FileField(upload_to='outputs/pdf/', blank=True, null=True)
    output_txt = models.FileField(upload_to='outputs/txt/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'ATS Analyses'

    def __str__(self):
        return f"Analysis #{self.pk} - {self.resume.original_filename}"


class ResumeHistory(models.Model):
    """Lightweight history log entry surfaced on the History page."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history_entries')
    analysis = models.ForeignKey(ATSAnalysis, on_delete=models.CASCADE, related_name='history_entries')
    action = models.CharField(max_length=100, default='optimization_completed')
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Resume History'

    def __str__(self):
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
