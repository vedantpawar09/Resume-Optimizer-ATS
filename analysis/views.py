import logging
import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files import File
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from resumes.models import Resume, JobDescription
from .models import ATSAnalysis, ResumeHistory
from .services.groq_client import GroqClient, GroqAPIError
from .services import prompts, scoring, rewriter

logger = logging.getLogger('resume_optimizer')


def _rate_limited(user) -> bool:
    key = f"ai_rate_limit_{user.id}"
    count = cache.get(key, 0)
    if count >= settings.AI_RATE_LIMIT_PER_MINUTE:
        return True
    cache.set(key, count + 1, timeout=60)
    return False


@login_required
def run_analysis(request, resume_id, jd_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    jd = get_object_or_404(JobDescription, id=jd_id, user=request.user)

    if request.method != 'POST':
        return render(request, 'analysis/confirm_analysis.html', {'resume': resume, 'jd': jd})

    if _rate_limited(request.user):
        messages.error(request, "You're sending AI requests too quickly. Please wait a minute and try again.")
        return redirect('analysis:confirm', resume_id=resume.id, jd_id=jd.id)

    client = GroqClient()
    try:
        # Step 1: ATS analysis only. The rewrite happens after the user
        # confirms which missing skills they actually have (see
        # confirm_missing_skills below) - we never silently add a skill the
        # candidate didn't vouch for.
        sys_p, user_p = prompts.ats_analysis_prompt(resume.raw_text, jd.raw_text)
        analysis_data = client.chat_json(sys_p, user_p)

        # Cross-check AI keyword lists with a deterministic fuzzy matcher.
        candidate_keywords = analysis_data.get('missing_keywords', []) + analysis_data.get('matched_keywords', [])
        matched_fuzzy, missing_fuzzy = scoring.fuzzy_keyword_match(resume.raw_text, candidate_keywords)

        analysis = ATSAnalysis.objects.create(
            user=request.user, resume=resume, job_description=jd,
            ats_score_before=analysis_data.get('ats_score_before', 0),
            keyword_match_percent=analysis_data.get('keyword_match_percent', 0),
            resume_match_percent=analysis_data.get('resume_match_percent', 0),
            skills_match_percent=analysis_data.get('skills_match_percent', 0),
            recruiter_match_percent=analysis_data.get('recruiter_match_percent', 0),
            formatting_score=analysis_data.get('formatting_score', 0),
            grammar_score=analysis_data.get('grammar_score', 0),
            readability_score=analysis_data.get('readability_score', 0),
            matched_keywords=matched_fuzzy or analysis_data.get('matched_keywords', []),
            missing_keywords=missing_fuzzy or analysis_data.get('missing_keywords', []),
            suggested_keywords=analysis_data.get('suggested_keywords', []),
            missing_skills=analysis_data.get('missing_skills', []),
            weak_sections=analysis_data.get('weak_sections', []),
            strong_sections=analysis_data.get('strong_sections', []),
            section_analysis=analysis_data.get('section_analysis', {}),
            ats_formatting_checks=analysis_data.get('ats_formatting_checks', {}),
            overall_summary=analysis_data.get('overall_summary', ''),
        )

        mode = request.POST.get('mode', 'full_optimize')
        if mode == 'score_only':
            ResumeHistory.objects.create(
                user=request.user, analysis=analysis, action='score_checked',
                note=f"{resume.original_filename} vs {jd.title or 'Job Description'} (score only)",
            )
            return redirect('analysis:results', analysis_id=analysis.id)

        return redirect('analysis:confirm_missing_skills', analysis_id=analysis.id)

    except GroqAPIError as exc:
        logger.exception("Groq analysis failed")
        messages.error(request, f"AI analysis failed: {exc}")
        return redirect('analysis:confirm', resume_id=resume.id, jd_id=jd.id)


@login_required
def confirm_missing_skills(request, analysis_id):
    """Ask the candidate, one by one, whether each skill/keyword the JD wants
    but their resume doesn't show is something they genuinely have. Only
    skills explicitly confirmed here are allowed into the rewrite - anything
    left unchecked (or the whole step skipped) is left out entirely."""
    analysis = get_object_or_404(ATSAnalysis, id=analysis_id, user=request.user)

    # Nothing to ask about - go straight to the rewrite.
    gaps = _combined_gaps(analysis)
    if not gaps:
        return _finalize_optimization(request, analysis, approved_keywords=[])

    if request.method == 'POST':
        if 'skip_all' in request.POST:
            approved = []
        else:
            approved = request.POST.getlist('approved_skill')
        return _finalize_optimization(request, analysis, approved_keywords=approved)

    return render(request, 'analysis/confirm_missing_skills.html', {'analysis': analysis, 'gaps': gaps})


def _combined_gaps(analysis) -> list:
    """Missing keywords and missing skills, de-duplicated, for the confirmation screen."""
    seen, gaps = set(), []
    for item in list(analysis.missing_skills) + list(analysis.missing_keywords):
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            gaps.append(item.strip())
    return gaps


def _finalize_optimization(request, analysis, approved_keywords):
    """Step 2: the actual AI rewrite, gated on the skills the candidate just
    confirmed they truly have, plus output file generation."""
    if _rate_limited(request.user):
        messages.error(request, "You're sending AI requests too quickly. Please wait a minute and try again.")
        return redirect('analysis:confirm_missing_skills', analysis_id=analysis.id)

    client = GroqClient()
    resume, jd = analysis.resume, analysis.job_description
    try:
        analysis.user_approved_keywords = approved_keywords
        sys_p2, user_p2 = prompts.resume_rewrite_prompt(
            resume.raw_text, jd.raw_text,
            analysis.missing_keywords, [w.get('section') for w in analysis.weak_sections],
            approved_keywords=approved_keywords,
        )
        rewrite_data = client.chat_json(sys_p2, user_p2, temperature=0.3)

        analysis.rewritten_sections = rewrite_data.get('rewritten_sections', {})
        analysis.change_log = rewrite_data.get('change_log', [])
        analysis.keywords_inserted = rewrite_data.get('keywords_inserted', [])
        analysis.ats_score_after = rewrite_data.get('projected_ats_score', analysis.ats_score_before)

        # Deterministic safety net: verify no hard facts (numbers, years, named
        # employers/tools) were silently dropped during the AI rewrite.
        rewritten_full_text = '\n'.join(analysis.rewritten_sections.values())
        analysis.fidelity_warnings = scoring.check_factual_fidelity(resume.raw_text, rewritten_full_text)
        analysis.save()

        _generate_output_files(analysis, resume)

        ResumeHistory.objects.create(
            user=request.user, analysis=analysis, action='optimization_completed',
            note=f"{resume.original_filename} vs {jd.title or 'Job Description'}",
        )
        return redirect('analysis:results', analysis_id=analysis.id)

    except GroqAPIError as exc:
        logger.exception("Groq rewrite failed")
        messages.error(request, f"AI rewrite failed: {exc}")
        return redirect('analysis:confirm_missing_skills', analysis_id=analysis.id)


def _generate_output_files(analysis: ATSAnalysis, resume: Resume):
    media_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', 'tmp')
    os.makedirs(media_dir, exist_ok=True)
    base_name = f"analysis_{analysis.id}"
    candidate_name = _candidate_name(resume)
    role_title = analysis.job_description.title or ''
    contact_line = rewriter.extract_contact_line(resume)

    txt_path = os.path.join(media_dir, f"{base_name}.txt")
    rewriter.build_txt(analysis.rewritten_sections, candidate_name, txt_path)
    with open(txt_path, 'rb') as f:
        analysis.output_txt.save(f"{base_name}.txt", File(f), save=False)

    if resume.file_type == 'docx':
        docx_path = os.path.join(media_dir, f"{base_name}.docx")
        try:
            rewriter.rewrite_docx_in_place(
                resume.file.path, resume.structured_sections, analysis.rewritten_sections, docx_path,
            )
        except Exception:  # noqa: BLE001
            logger.exception("In-place DOCX rewrite failed, falling back to clean template")
            rewriter.build_clean_docx(analysis.rewritten_sections, candidate_name, docx_path,
                                       role_title=role_title, contact_line=contact_line)
        with open(docx_path, 'rb') as f:
            analysis.output_docx.save(f"{base_name}.docx", File(f), save=False)
    else:
        docx_path = os.path.join(media_dir, f"{base_name}.docx")
        rewriter.build_clean_docx(analysis.rewritten_sections, candidate_name, docx_path,
                                   role_title=role_title, contact_line=contact_line)
        with open(docx_path, 'rb') as f:
            analysis.output_docx.save(f"{base_name}.docx", File(f), save=False)

    pdf_path = os.path.join(media_dir, f"{base_name}.pdf")
    rewriter.build_clean_pdf(analysis.rewritten_sections, candidate_name, pdf_path,
                              role_title=role_title, contact_line=contact_line)
    with open(pdf_path, 'rb') as f:
        analysis.output_pdf.save(f"{base_name}.pdf", File(f), save=False)

    analysis.save()


@login_required
def confirm_analysis(request, resume_id, jd_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    jd = get_object_or_404(JobDescription, id=jd_id, user=request.user)
    return render(request, 'analysis/confirm_analysis.html', {'resume': resume, 'jd': jd})


@login_required
def results(request, analysis_id):
    analysis = get_object_or_404(ATSAnalysis, id=analysis_id, user=request.user)
    candidate_name = _candidate_name(analysis.resume)
    full_resume_text = rewriter.assemble_full_resume_text(analysis.rewritten_sections, candidate_name)
    return render(request, 'analysis/results.html', {
        'analysis': analysis, 'full_resume_text': full_resume_text,
        'still_missing_keywords': _still_missing_keywords(analysis, full_resume_text),
    })


@login_required
def compare(request, analysis_id):
    analysis = get_object_or_404(ATSAnalysis, id=analysis_id, user=request.user)
    candidate_name = _candidate_name(analysis.resume)
    full_resume_text = rewriter.assemble_full_resume_text(analysis.rewritten_sections, candidate_name)
    return render(request, 'analysis/compare.html', {
        'analysis': analysis, 'full_resume_text': full_resume_text,
    })


_NAME_BLOCKLIST = {
    'with', 'developer', 'experience', 'skilled', 'python', 'java', 'summary',
    'resume', 'curriculum', 'vitae', 'professional', 'engineer', 'specialist',
    'manager', 'years', 'building', 'strong', 'knowledge', 'developing',
    'software', 'hands-on', 'proven', 'passionate', 'seeking', 'motivated',
}


def _looks_like_name(candidate: str) -> bool:
    if not candidate or len(candidate) > 40:
        return False
    words = candidate.split()
    if not (1 <= len(words) <= 4):
        return False
    return not any(w.lower() in _NAME_BLOCKLIST for w in words)


def _trim_name_candidate(text: str) -> str:
    """Cut a raw line at the first sign it has drifted from 'name' into
    contact info or prose (comma, pipe, @, digit), then keep only a
    name-sized number of words."""
    positions = [text.find(c) for c in (',', '|', '@', '\t')]
    digit_match = re.search(r'\d', text)
    if digit_match:
        positions.append(digit_match.start())
    positions = [p for p in positions if p > 0]
    if positions:
        text = text[:min(positions)]
    words = text.split()
    return ' '.join(words[:4]).strip()


def _candidate_name(resume) -> str:
    """Extract just the candidate's name for use as a document title/header.
    Deliberately conservative: a hardened, multi-step fallback so a parsing
    hiccup can never dump an entire paragraph into a document title."""
    header = resume.structured_sections.get('header', '') if resume.structured_sections else ''
    first_line = next((ln.strip() for ln in header.splitlines() if ln.strip()), '')

    candidate = _trim_name_candidate(first_line)
    if _looks_like_name(candidate):
        return candidate

    # Fallback: look for the first 2-3 consecutive Title-Case words anywhere
    # in the header block, which is almost always the candidate's name even
    # if line breaks got lost during PDF text extraction.
    match = re.search(r"\b[A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){1,2}\b", header)
    if match:
        candidate = match.group(0)
        if _looks_like_name(candidate):
            return candidate

    return 'Candidate'


def _still_missing_keywords(analysis, full_resume_text: str) -> list:
    """Of the keywords flagged as missing during the initial analysis, which
    ones actually made it into the rewritten resume (via keywords_inserted or
    simply because they now appear in the text) vs which are genuinely still
    absent - shown to the user so they know what, if anything, to add by hand."""
    inserted_lower = {k.lower() for k in analysis.keywords_inserted}
    resume_lower = full_resume_text.lower()
    still_missing = []
    for kw in analysis.missing_keywords:
        if kw.lower() in inserted_lower or kw.lower() in resume_lower:
            continue
        still_missing.append(kw)
    return still_missing


@login_required
def download(request, analysis_id, file_format):
    analysis = get_object_or_404(ATSAnalysis, id=analysis_id, user=request.user)
    if file_format not in ('docx', 'pdf', 'txt'):
        return HttpResponseForbidden("Invalid file format requested.")
    field_map = {'docx': analysis.output_docx, 'pdf': analysis.output_pdf, 'txt': analysis.output_txt}
    file_field = field_map.get(file_format)
    if not file_field:
        messages.error(request, "This resume hasn't been optimized yet - run the full optimization to generate downloadable files.")
        return redirect('analysis:results', analysis_id=analysis.id)
    return FileResponse(file_field.open('rb'), as_attachment=True, filename=os.path.basename(file_field.name))
