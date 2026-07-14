from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    THEME_CHOICES = (('light', 'Light'), ('dark', 'Dark'))

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    groq_api_key_override = models.CharField(
        max_length=255, blank=True,
        help_text="Optional: use your own Groq API key instead of the server default.",
    )
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    job_title = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.username}"
