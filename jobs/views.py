from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
import json

from .models import JobDescription, AnalysisRun, MatchResult
from .forms import JobDescriptionForm
from .services import JobDescriptionService, AnalysisService, RecommendationService


class JobDescriptionListView(LoginRequiredMixin, ListView):
    model = JobDescription
    template_name = 'jobs/list.html'
    context_object_name = 'job_descriptions'
    paginate_by = 10

    def get_queryset(self):
        return JobDescription.objects.filter(
            owner=self.request.user
        ).order_by('-created_at')


class JobDescriptionDetailView(LoginRequiredMixin, DetailView):
    model = JobDescription
    template_name = 'jobs/detail.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return JobDescription.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.get_object()

        # Get recent analyses
        recent_analyses = AnalysisRun.objects.filter(
            job_description=job,
            actor=self.request.user
        ).order_by('-created_at')[:5]

        context['recent_analyses'] = recent_analyses
        context['structured_data'] = job.structured_json

        return context


class JobDescriptionCreateView(LoginRequiredMixin, CreateView):
    model = JobDescription
    form_class = JobDescriptionForm
    template_name = 'jobs/create.html'
    success_url = reverse_lazy('jobs:list')

    def form_valid(self, form):
        form.instance.owner = self.request.user

        # Create job description with AI structuring
        job = JobDescriptionService.create_job_description(
            owner=self.request.user,
            title=form.cleaned_data['title'],
            company=form.cleaned_data.get('company', ''),
            raw_text=form.cleaned_data['raw_text'],
            location=form.cleaned_data.get('location', ''),
            salary_range=form.cleaned_data.get('salary_range', ''),
            min_years_experience=form.cleaned_data.get('min_years_experience'),
            degree_requirements=form.cleaned_data.get('degree_requirements', '')
        )

        messages.success(self.request, 'Job description created successfully!')
        return redirect('jobs:detail', pk=job.id)


class JobDescriptionEditView(LoginRequiredMixin, UpdateView):
    model = JobDescription
    form_class = JobDescriptionForm
    template_name = 'jobs/edit.html'
    success_url = reverse_lazy('jobs:list')

    def get_queryset(self):
        return JobDescription.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        job = self.get_object()
        job.title = form.cleaned_data['title']
        job.company = form.cleaned_data.get('company', '')
        job.raw_text = form.cleaned_data['raw_text']
        job.location = form.cleaned_data.get('location', '')
        job.salary_range = form.cleaned_data.get('salary_range', '')
        job.min_years_experience = form.cleaned_data.get('min_years_experience')
        job.degree_requirements = form.cleaned_data.get('degree_requirements', '')
        job.save()

        # Re-analyze with AI
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            JobDescriptionService.analyze_job_description(job)
        )

        messages.success(self.request, 'Job description updated successfully!')
        return super().form_valid(form)


class JobDescriptionDeleteView(LoginRequiredMixin, DeleteView):
    model = JobDescription
    template_name = 'jobs/confirm_delete.html'
    success_url = reverse_lazy('jobs:list')

    def get_queryset(self):
        return JobDescription.objects.filter(owner=self.request.user)


class AnalysisRunDetailView(LoginRequiredMixin, DetailView):
    model = AnalysisRun
    template_name = 'jobs/analysis_detail.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return AnalysisRun.objects.filter(actor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analysis = self.get_object()

        # Get match results
        results = MatchResult.objects.filter(
            analysis_run=analysis
        ).order_by('-overall_score')

        context['results'] = results
        context['job_description'] = analysis.job_description

        return context


def run_analysis_view(request):
    """Run analysis on selected resumes"""
    if request.method == 'POST':
        resume_ids = request.POST.getlist('resume_ids')
        job_description_id = request.POST.get('job_description_id')

        if not resume_ids or not job_description_id:
            messages.error(request, 'Please select resumes and a job description')
            return redirect('jobs:list')

        try:
            import asyncio
            loop = asyncio.new_event_loop()
            analysis = loop.run_until_complete(
                AnalysisService.run_analysis(
                    actor=request.user,
                    actor_role='talent',
                    resume_ids=resume_ids,
                    job_description_id=job_description_id
                )
            )

            messages.success(request, f'Analysis started! Analysis ID: {analysis.id}')
            return redirect('jobs:analysis_detail', pk=analysis.id)

        except Exception as e:
            messages.error(request, f'Error starting analysis: {str(e)}')
            return redirect('jobs:list')

    return redirect('jobs:list')


def get_recommendations_view(request, resume_id, job_description_id):
    """Get improvement recommendations for a resume"""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        recommendations = loop.run_until_complete(
            RecommendationService.generate_resume_improvements(
                resume_id, job_description_id
            )
        )

        return JsonResponse(recommendations)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_candidate_ranking_view(request, job_description_id):
    """Get ranked candidates for a job description"""
    try:
        resume_ids = request.GET.getlist('resume_ids[]')
        ranking = AnalysisService.get_candidate_ranking(job_description_id, resume_ids)

        return JsonResponse({'ranking': ranking})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def analyze_job_description_text(request):
    """Analyze job description text and return structured data"""
    if request.method == 'POST':
        try:
            text = request.POST.get('text', '')
            if not text:
                return JsonResponse({'error': 'No text provided'}, status=400)

            # Create temporary job description
            job = JobDescriptionService.create_job_description(
                owner=request.user,
                title='Temporary Analysis',
                raw_text=text
            )

            return JsonResponse({
                'structured_data': job.structured_json,
                'requirements_required': job.requirements_required,
                'requirements_preferred': job.requirements_preferred,
                'skills_required': job.skills_required,
                'skills_preferred': job.skills_preferred
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
