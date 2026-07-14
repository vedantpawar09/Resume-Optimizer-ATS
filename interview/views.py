import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from analysis.models import ATSAnalysis
from analysis.services.groq_client import GroqClient, GroqAPIError
from analysis.services import prompts
from .models import InterviewQuestionSet, MockInterviewSession, MockInterviewAnswer

logger = logging.getLogger('resume_optimizer')


@login_required
def generate_questions(request, analysis_id):
    analysis = get_object_or_404(ATSAnalysis, id=analysis_id, user=request.user)
    existing = InterviewQuestionSet.objects.filter(analysis=analysis).first()
    if existing:
        return render(request, 'interview/questions.html', {'analysis': analysis, 'qset': existing})

    if request.method == 'POST':
        client = GroqClient()
        resume_text = analysis.resume.raw_text
        try:
            sys_p, user_p = prompts.interview_questions_prompt(resume_text, analysis.job_description.raw_text)
            data = client.chat_json(sys_p, user_p, max_tokens=6000)
            qset = InterviewQuestionSet.objects.create(
                user=request.user, analysis=analysis,
                questions=data.get('questions', []),
                top_20_hr=data.get('top_20_hr', []),
                top_20_technical=data.get('top_20_technical', []),
                top_10_resume_based=data.get('top_10_resume_based', []),
                top_10_project_based=data.get('top_10_project_based', []),
            )
            return render(request, 'interview/questions.html', {'analysis': analysis, 'qset': qset})
        except GroqAPIError as exc:
            messages.error(request, f"Could not generate interview questions: {exc}")
            return redirect('analysis:results', analysis_id=analysis.id)

    return render(request, 'interview/generate.html', {'analysis': analysis})


@login_required
def mock_interview(request, qset_id):
    qset = get_object_or_404(InterviewQuestionSet, id=qset_id, user=request.user)
    session, _ = MockInterviewSession.objects.get_or_create(
        user=request.user, question_set=qset, completed=False,
    )
    return render(request, 'interview/mock_interview.html', {'qset': qset, 'session': session})


@login_required
@require_POST
@csrf_protect
def submit_mock_answer(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    body = json.loads(request.body or '{}')
    question = body.get('question', '')
    category = body.get('category', '')
    user_answer = body.get('answer', '')

    if not user_answer.strip():
        return JsonResponse({'error': 'Please type an answer before submitting.'}, status=400)

    client = GroqClient()
    try:
        sys_p, user_p = prompts.mock_interview_feedback_prompt(question, category, user_answer)
        data = client.chat_json(sys_p, user_p)
    except GroqAPIError as exc:
        return JsonResponse({'error': str(exc)}, status=502)

    answer = MockInterviewAnswer.objects.create(
        session=session, question=question, category=category, user_answer=user_answer,
        confidence_score=data.get('confidence_score', 0),
        grammar_score=data.get('grammar_score', 0),
        technical_accuracy_score=data.get('technical_accuracy_score', 0),
        communication_score=data.get('communication_score', 0),
        star_method_used=data.get('star_method_used', False),
        overall_score=data.get('overall_score', 0),
        strengths=data.get('strengths', []),
        improvements=data.get('improvements', []),
        model_answer=data.get('model_answer', ''),
    )
    return JsonResponse({
        'confidence_score': answer.confidence_score,
        'grammar_score': answer.grammar_score,
        'technical_accuracy_score': answer.technical_accuracy_score,
        'communication_score': answer.communication_score,
        'star_method_used': answer.star_method_used,
        'overall_score': answer.overall_score,
        'strengths': answer.strengths,
        'improvements': answer.improvements,
        'model_answer': answer.model_answer,
    })


@login_required
@require_POST
def complete_mock_session(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    session.completed = True
    session.save()
    return JsonResponse({'status': 'completed'})
