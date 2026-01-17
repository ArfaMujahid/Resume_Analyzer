from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.core.files.storage import default_storage
import uuid
import os

from .models import ResumeDocument, ParsedResume
from .forms import ResumeUploadForm
from .services import DocumentParserService


class ResumeListView(LoginRequiredMixin, ListView):
    model = ResumeDocument
    template_name = 'resumes/list.html'
    context_object_name = 'resumes'
    paginate_by = 10

    def get_queryset(self):
        return ResumeDocument.objects.filter(
            owner=self.request.user
        ).order_by('-created_at')


class ResumeDetailView(LoginRequiredMixin, DetailView):
    model = ResumeDocument
    template_name = 'resumes/detail.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return ResumeDocument.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resume = self.get_object()

        # Get parsed data if available
        try:
            parsed = ParsedResume.objects.get(resume=resume)
            context['parsed_resume'] = parsed
            context['structured_data'] = parsed.structured_json
        except ParsedResume.DoesNotExist:
            context['parsed_resume'] = None
            context['structured_data'] = None

        return context


class ResumeUploadView(LoginRequiredMixin, CreateView):
    model = ResumeDocument
    form_class = ResumeUploadForm
    template_name = 'resumes/upload.html'
    success_url = reverse_lazy('resumes:list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.source_type = 'talent_upload'

        # Handle file upload
        uploaded_file = self.request.FILES['file']
        file_content = uploaded_file.read()

        # Validate file
        is_valid, message = DocumentParserService.validate_file(file_content, uploaded_file.name)
        if not is_valid:
            form.add_error('file', message)
            return self.form_invalid(form)

        # Generate file hash
        file_hash = DocumentParserService.get_file_hash(file_content)

        # Check for duplicates
        existing = ResumeDocument.objects.filter(
            owner=self.request.user,
            checksum_hash=file_hash
        ).first()

        if existing:
            messages.warning(self.request, f'A file with this content already exists: {existing.original_filename}')
            return redirect('resumes:detail', pk=existing.id)

        # Save file
        file_extension = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
        filename = f"resumes/{self.request.user.id}/{uuid.uuid4()}.{file_extension}"

        # Create the resume document
        resume = form.save(commit=False)
        resume.original_filename = uploaded_file.name
        resume.file_type = file_extension
        resume.file_size_bytes = len(file_content)
        resume.checksum_hash = file_hash
        resume.storage_ref = filename

        # Save file to storage
        path = default_storage.save(filename, ContentFile(file_content))
        resume.save()

        messages.success(self.request, 'Resume uploaded successfully! Processing...')

        # Trigger parsing
        from .tasks import parse_resume_task
        parse_resume_task.delay(resume.id)

        return super().form_valid(form)


class ResumeEditView(LoginRequiredMixin, UpdateView):
    model = ResumeDocument
    template_name = 'resumes/edit.html'
    fields = ['original_filename']
    success_url = reverse_lazy('resumes:list')

    def get_queryset(self):
        return ResumeDocument.objects.filter(owner=self.request.user)


class ResumeDeleteView(LoginRequiredMixin, DeleteView):
    model = ResumeDocument
    template_name = 'resumes/confirm_delete.html'
    success_url = reverse_lazy('resumes:list')

    def get_queryset(self):
        return ResumeDocument.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        resume = self.get_object()

        # Delete file from storage
        if default_storage.exists(resume.storage_ref):
            default_storage.delete(resume.storage_ref)

        # Delete parsed data
        ParsedResume.objects.filter(resume=resume).delete()

        messages.success(request, 'Resume deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ResumeDownloadView(LoginRequiredMixin, DetailView):
    model = ResumeDocument
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return ResumeDocument.objects.filter(owner=self.request.user)

    def get(self, request, *args, **kwargs):
        resume = self.get_object()

        if not default_storage.exists(resume.storage_ref):
            raise Http404("File not found")

        # Serve the file
        response = HttpResponse(
            default_storage.open(resume.storage_ref).read(),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{resume.original_filename}"'
        return response


def reparse_resume(request, pk):
    """Reparse a resume document"""
    if request.method == 'POST':
        resume = get_object_or_404(ResumeDocument, pk=pk, owner=request.user)

        # Delete existing parsed data
        ParsedResume.objects.filter(resume=resume).delete()

        # Reset status
        resume.status = 'uploaded'
        resume.parsing_error = None
        resume.save()

        # Trigger parsing
        from .tasks import parse_resume_task
        parse_resume_task.delay(resume.id)

        messages.success(request, 'Resume sent for re-parsing!')
        return redirect('resumes:detail', pk=pk)

    return redirect('resumes:detail', pk=pk)
