from django import forms
from django.conf import settings

from .models import Resume, JobDescription


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control d-none',
                'id': 'resume-file-input',
                'accept': '.pdf,.docx',
            }),
        }

    def clean_file(self):
        f = self.cleaned_data['file']
        ext = ('.' + f.name.rsplit('.', 1)[-1]).lower() if '.' in f.name else ''
        if ext not in settings.ALLOWED_RESUME_EXTENSIONS:
            raise forms.ValidationError("Only PDF and DOCX files are supported.")
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if f.size > max_bytes:
            raise forms.ValidationError(f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB.")
        return f


class JobDescriptionForm(forms.ModelForm):
    class Meta:
        model = JobDescription
        fields = ['title', 'company', 'raw_text', 'source_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title (optional)'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company (optional)'}),
            'raw_text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 12, 'id': 'jd-textarea',
                'placeholder': 'Paste the full job description here...',
            }),
            'source_file': forms.ClearableFileInput(attrs={'class': 'form-control d-none', 'id': 'jd-file-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('raw_text') and not cleaned.get('source_file'):
            raise forms.ValidationError("Paste a job description or upload a JD file.")
        return cleaned
