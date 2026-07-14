import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ResumeUploadForm, JobDescriptionForm
from .models import Resume, JobDescription
from .utils.parsers import extract_text, split_into_sections, ParsingError

logger = logging.getLogger('resume_optimizer')


@login_required
def upload_resume(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            f = form.cleaned_data['file']
            resume.original_filename = f.name
            resume.file_type = f.name.rsplit('.', 1)[-1].lower()
            resume.file_size_kb = max(1, f.size // 1024)

            try:
                text = extract_text(f, resume.file_type)
            except ParsingError as exc:
                logger.exception("Resume parsing failed for %s", f.name)
                messages.error(request, f"Could not read that file: {exc}")
                return render(request, 'resumes/upload_resume.html', {'form': form})

            if not text.strip():
                messages.error(request, "We couldn't find any readable text in that file. "
                                         "It may be a scanned image — try exporting a text-based PDF or DOCX.")
                return render(request, 'resumes/upload_resume.html', {'form': form})

            resume.raw_text = text
            resume.structured_sections = split_into_sections(text)
            resume.save()
            messages.success(request, "Resume uploaded and parsed successfully.")
            return redirect(reverse('resumes:add_job_description') + f'?resume_id={resume.id}')
    else:
        form = ResumeUploadForm()
    recent = Resume.objects.filter(user=request.user)[:5]
    return render(request, 'resumes/upload_resume.html', {'form': form, 'recent': recent})


@login_required
def add_job_description(request):
    resume_id = request.GET.get('resume_id') or request.POST.get('resume_id')
    resume = get_object_or_404(Resume, id=resume_id, user=request.user) if resume_id else None

    if request.method == 'POST':
        form = JobDescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            jd = form.save(commit=False)
            jd.user = request.user
            if jd.source_file and not jd.raw_text.strip():
                try:
                    text = extract_text(jd.source_file, 'pdf')
                    jd.raw_text = text
                except ParsingError as exc:
                    messages.error(request, f"Could not read the JD file: {exc}")
                    return render(request, 'resumes/add_job_description.html', {'form': form, 'resume': resume})
            jd.save()
            if not resume:
                messages.error(request, "Please upload a resume first.")
                return redirect('resumes:upload_resume')
            return redirect('analysis:run_analysis', resume_id=resume.id, jd_id=jd.id)
    else:
        form = JobDescriptionForm()
    return render(request, 'resumes/add_job_description.html', {'form': form, 'resume': resume})


@login_required
@require_http_methods(['GET'])
def resume_preview(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    return render(request, 'resumes/_preview_fragment.html', {'resume': resume})
