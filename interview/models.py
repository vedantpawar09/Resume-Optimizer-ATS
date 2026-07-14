from django.db import models
from django.contrib.auth.models import User

from analysis.models import ATSAnalysis


class InterviewQuestionSet(models.Model):
    """A generated batch of interview questions tied to one analysis."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_sets')
    analysis = models.ForeignKey(ATSAnalysis, on_delete=models.CASCADE, related_name='question_sets')
    questions = models.JSONField(default=list, blank=True)
    top_20_hr = models.JSONField(default=list, blank=True)
    top_20_technical = models.JSONField(default=list, blank=True)
    top_10_resume_based = models.JSONField(default=list, blank=True)
    top_10_project_based = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Question set #{self.pk} for analysis #{self.analysis_id}"


class MockInterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mock_sessions')
    question_set = models.ForeignKey(InterviewQuestionSet, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Mock session #{self.pk}"


class MockInterviewAnswer(models.Model):
    session = models.ForeignKey(MockInterviewSession, on_delete=models.CASCADE, related_name='answers')
    question = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    user_answer = models.TextField()

    confidence_score = models.PositiveIntegerField(default=0)
    grammar_score = models.PositiveIntegerField(default=0)
    technical_accuracy_score = models.PositiveIntegerField(default=0)
    communication_score = models.PositiveIntegerField(default=0)
    star_method_used = models.BooleanField(default=False)
    overall_score = models.PositiveIntegerField(default=0)
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    model_answer = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question[:50]}"
