"""
Prompt engineering for every AI feature in the app.

Design principles used throughout:
 - System prompts pin down role, tone, and STRICT JSON output schema so
   responses are parseable without brittle regex.
 - The rewriting prompt explicitly forbids AI-cliche phrasing ("leverage",
   "spearheaded synergies", "dynamic go-getter", em-dash chains, etc.),
   asks for varied sentence length, first-person implied voice, and
   concrete numbers - all measurable factors that AI-text detectors and
   human recruiters both key on. This nudges output toward natural,
   human-edited phrasing; it is not a guaranteed bypass of any detector.
"""

HUMAN_VOICE_RULES = """
Writing style rules (apply to every piece of generated resume text):
- Write the way a skilled human recruiter edits a resume: plain, confident, specific.
- Vary sentence length. Do not make every bullet the same word count or the same
  "Verb + adjective + noun" template.
- Never use these overused AI phrases: "leverage", "spearheaded", "dynamic",
  "synergy", "utilize", "cutting-edge", "passionate about", "results-driven
  professional", "proven track record", "seamlessly", "robust solution",
  "delve into", "in today's fast-paced world".
- Prefer concrete numbers and specific tools/technologies over vague adjectives.
- Do not start every bullet point with the same verb.
- Avoid repeating the exact keyword list mechanically - weave keywords into
  natural sentences describing real work.
- Keep the person's original achievements and facts; do not invent employers,
  dates, titles, or metrics that were not implied by the original resume.
- No keyword stuffing: each keyword should appear where it genuinely fits.
"""


def ats_analysis_prompt(resume_text: str, jd_text: str) -> tuple[str, str]:
    system = f"""You are a senior ATS (Applicant Tracking System) analyst and technical recruiter
with 20 years of experience screening resumes for Fortune 500 companies.
Compare the RESUME against the JOB DESCRIPTION and return a single JSON object only,
no markdown, no commentary, matching exactly this schema:

{{
  "ats_score_before": <int 0-100>,
  "keyword_match_percent": <int 0-100>,
  "resume_match_percent": <int 0-100>,
  "skills_match_percent": <int 0-100>,
  "recruiter_match_percent": <int 0-100>,
  "formatting_score": <int 0-100>,
  "grammar_score": <int 0-100>,
  "readability_score": <int 0-100>,
  "matched_keywords": [<string>, ...],
  "missing_keywords": [<string>, ...],
  "suggested_keywords": [<string>, ...],
  "missing_skills": [<string>, ...],
  "weak_sections": [{{"section": <string>, "issue": <string>}}, ...],
  "strong_sections": [<string>, ...],
  "section_analysis": {{
      "summary": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "experience": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "projects": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "education": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "skills": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "certifications": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "achievements": {{"present": <bool>, "quality": <string>, "comment": <string>}},
      "languages": {{"present": <bool>, "quality": <string>, "comment": <string>}}
  }},
  "ats_formatting_checks": {{
      "tables_detected": <bool>,
      "columns_detected": <bool>,
      "images_or_icons_detected": <bool>,
      "contact_info_present": <bool>,
      "standard_section_headings": <bool>,
      "bullet_points_used": <bool>,
      "action_verbs_used": <bool>,
      "quantified_impact": <bool>
  }},
  "overall_summary": <string, 3-4 sentences>
}}
Be strict and realistic with scoring - do not default to high numbers."""

    user = f"""RESUME:
\"\"\"{resume_text}\"\"\"

JOB DESCRIPTION:
\"\"\"{jd_text}\"\"\"

Return only the JSON object described in the system prompt."""
    return system, user


def resume_rewrite_prompt(resume_text: str, jd_text: str, missing_keywords: list,
                          weak_sections: list, approved_keywords: list = None) -> tuple[str, str]:
    approved_keywords = approved_keywords or []
    system = f"""You are an expert resume writer and technical recruiter who rewrites resume
CONTENT ONLY - never structure. You will be given the original resume text (with its
section headings) and a job description. Rewrite the resume so it is more competitive
for this specific job while preserving:
 - the exact same section headings and their order
 - the exact same employers, job titles, and dates
 - the exact same overall length range (do not double the resume length)

ACCURACY IS THE TOP PRIORITY - more important than polish or creativity:
 - Every number, percentage, dollar amount, year, team size, and metric in the
   original resume MUST appear in your rewrite, unchanged. Never invent, round,
   or drop a number.
 - Every employer name, school name, job title, certification name, and named
   technology/tool in the original MUST still appear in your rewrite.
 - You are only allowed to change: sentence structure, word choice, verb choice,
   and which existing keywords are emphasized. You are NOT allowed to add new
   achievements, employers, tools, or metrics that are not implied by the original.
 - If you are unsure whether a change would alter a fact, do not make that change.

MISSING KEYWORDS/SKILLS - STRICT APPROVAL RULE:
 - The candidate was shown every keyword/skill from the job description that their
   original resume does not demonstrate, and explicitly told the app which ones they
   truly have. The APPROVED list below is the ONLY set of missing keywords/skills you
   may add to the resume.
 - APPROVED (candidate confirmed they have real experience with these - safe to
   naturally weave into relevant sections): {approved_keywords}
 - Any other missing keyword NOT in the approved list above must be left OUT of the
   rewrite entirely, even if it would raise the ATS score - the candidate did not
   confirm they actually have it, so adding it would be dishonest.

TARGET: aim for a projected ATS score of 90 or above whenever the candidate's real
experience (including the approved keywords above) can honestly support it. To get
there:
 - Work in every approved keyword above wherever it has a truthful, natural home in
   the candidate's existing experience.
 - Mirror the job description's own terminology where the candidate's experience
   genuinely matches it (e.g. if the JD says "CI/CD pipelines" and the resume already
   describes automated deployment work, use "CI/CD pipelines").
 - Strengthen weak sections identified below so they read as accomplishments with
   scope and impact, not just duties - using only facts already present in the
   original resume plus the approved keywords.
 - If, after doing all of this honestly, the resume still cannot reach 90+ because it
   truly lacks matching experience, report the realistic score instead of inflating it -
   never claim a high score you can't justify from the actual content.

{HUMAN_VOICE_RULES}

FORMATTING for sections that list multiple positions or degrees (experience,
work history, education, etc.): format EACH entry using exactly this 3-part
line structure, with a blank line between separate entries:
  Line 1: "<Organization or School Name> | <Start Date> - <End Date>"
  Line 2: "<Job Title or Degree Name>"
  Line 3+: one or more "- " bullet points describing the role/achievements
This is a layout instruction only - it must not change any employer name,
title, or date, only which line each already-true detail sits on.

SUMMARY / ABOUT ME SECTION - this is the section a recruiter reads first, so
give it special care: rewrite it as a short, specific pitch for THIS exact
job, not a generic bio. It should:
 - Open by naming (or clearly implying) the target role or field, so it
   reads as written for this job, not recycled for any job.
 - Reference 2-4 of the candidate's real, strongest skills/experiences that
   most directly match what the job description is asking for - pulled only
   from what's already true in the original resume (plus any approved
   keywords above).
 - State the fit plainly - what the candidate brings that lines up with this
   role's actual requirements - in 3-5 sentences total, no filler sentences
   that could apply to any candidate in any field.
 - Still follow every rule above: no invented experience, no banned AI
   phrases, no keyword stuffing.

Return a single JSON object only, no markdown, matching exactly this schema:
{{
  "rewritten_sections": {{ "<section_heading_as_in_original>": "<rewritten section text>", ... }},
  "change_log": [
     {{"section": <string>, "change_type": "added|modified|removed",
       "before": <string>, "after": <string>, "reason": <string>}}
  ],
  "keywords_inserted": [<string>, ...],
  "projected_ats_score": <int 0-100>
}}"""

    user = f"""ORIGINAL RESUME (with section headings):
\"\"\"{resume_text}\"\"\"

JOB DESCRIPTION:
\"\"\"{jd_text}\"\"\"

MISSING KEYWORDS FROM INITIAL ANALYSIS (do NOT add unless also in the approved list): {missing_keywords}

CANDIDATE-APPROVED KEYWORDS (safe to add): {approved_keywords}

WEAK SECTIONS TO IMPROVE: {weak_sections}

Before returning your answer, silently double-check: (1) every number, date,
employer, title, and named technology from the original resume still appears
somewhere in your rewritten_sections, and (2) you have not added any missing
keyword that isn't in the candidate-approved list. Return only the JSON object."""
    return system, user


def interview_questions_prompt(resume_text: str, jd_text: str, count: int = 60) -> tuple[str, str]:
    system = """You are a panel of interviewers (technical lead, HR manager, and hiring
manager) preparing questions for a candidate based on their resume and a job description.
Return a single JSON object only, no markdown, matching exactly this schema:

{
  "questions": [
    {
      "question": <string>,
      "category": "Technical|HR|Projects|Experience|Coding|Behavioral|Scenario Based|Leadership|System Design|Database|Cloud|AI|Java|Python|React|Spring Boot|Django|SQL|Networking|Resume Based",
      "why_asked": <string>,
      "sample_answer": <string>,
      "best_answer_tips": <string>,
      "difficulty": "Easy|Medium|Hard"
    }
  ],
  "top_20_hr": [<string>, ...],
  "top_20_technical": [<string>, ...],
  "top_10_resume_based": [<string>, ...],
  "top_10_project_based": [<string>, ...]
}"""

    user = f"""CANDIDATE RESUME:
\"\"\"{resume_text}\"\"\"

JOB DESCRIPTION:
\"\"\"{jd_text}\"\"\"

Generate {count} interview questions in the "questions" array, covering a realistic mix
of categories based on what actually appears in this resume and job description (only
include technology-specific categories like Java/Python/React/Django/SQL/Cloud if those
technologies genuinely appear). Then also fill top_20_hr, top_20_technical,
top_10_resume_based, and top_10_project_based as short question-string lists (these can
overlap with the main list). Return only the JSON object."""
    return system, user


def mock_interview_feedback_prompt(question: str, category: str, user_answer: str) -> tuple[str, str]:
    system = """You are an experienced interview coach evaluating a candidate's spoken/typed
answer to an interview question. Return a single JSON object only, no markdown, matching
exactly this schema:
{
  "confidence_score": <int 0-100>,
  "grammar_score": <int 0-100>,
  "technical_accuracy_score": <int 0-100>,
  "communication_score": <int 0-100>,
  "star_method_used": <bool>,
  "overall_score": <int 0-100>,
  "strengths": [<string>, ...],
  "improvements": [<string>, ...],
  "model_answer": <string>
}"""
    user = f"""QUESTION ({category}): {question}

CANDIDATE'S ANSWER:
\"\"\"{user_answer}\"\"\"

Evaluate the answer and return only the JSON object."""
    return system, user