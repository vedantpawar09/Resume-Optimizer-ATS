from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render, redirect

from analysis.models import ATSAnalysis, ResumeHistory
from authentication.forms import ProfileSettingsForm
from authentication.models import UserProfile


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'dashboard/landing.html')


@login_required
def home(request):
    analyses = ATSAnalysis.objects.filter(user=request.user)
    stats = {
        'total_optimizations': analyses.count(),
        'avg_score_before': round(analyses.aggregate(v=Avg('ats_score_before'))['v'] or 0),
        'avg_score_after': round(analyses.aggregate(v=Avg('ats_score_after'))['v'] or 0),
    }
    recent = analyses[:5]
    chart_labels = [a.created_at.strftime('%b %d') for a in reversed(list(analyses[:10]))]
    chart_before = [a.ats_score_before for a in reversed(list(analyses[:10]))]
    chart_after = [a.ats_score_after for a in reversed(list(analyses[:10]))]
    context = {
        'stats': stats, 'recent': recent,
        'chart_labels': chart_labels, 'chart_before': chart_before, 'chart_after': chart_after,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def history(request):
    entries = ResumeHistory.objects.filter(user=request.user).select_related('analysis', 'analysis__resume')
    return render(request, 'dashboard/history.html', {'entries': entries})


@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect('dashboard:settings')
    else:
        form = ProfileSettingsForm(instance=profile)
    return render(request, 'dashboard/settings.html', {'form': form})
