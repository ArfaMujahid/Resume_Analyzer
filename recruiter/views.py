from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import os
import tempfile
import uuid
import json
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

from jobs.models import JobDescription
from ai.services import openrouter_service
from talent.views import extract_text_from_pdf, extract_text_from_docx

class RecruiterDashboardView(TemplateView):
    template_name = 'recruiter/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current batch from session
        batch = self.request.session.get('recruiter_batch', {})
        context['current_batch'] = batch

        # Statistics from session
        context['resume_count'] = len(batch.get('resumes', []))
        context['status'] = batch.get('status', 'ready')
        context['results_count'] = len(batch.get('results', []))

        return context

@csrf_exempt
@require_POST
def upload_batch(request):
    """Upload multiple resumes for batch processing"""
    try:
        # Initialize session
        if 'recruiter_batch' not in request.session:
            request.session['recruiter_batch'] = {
                'batch_id': str(uuid.uuid4()),
                'created_at': time.time(),
                'resumes': [],
                'results': [],
                'status': 'uploading'
            }
            request.session.save()

        batch = request.session['recruiter_batch']
        session_dir = f'/tmp/recruiter_sessions/{request.session.session_key}'
        os.makedirs(session_dir, exist_ok=True)

        # Process uploaded files
        files = request.FILES.getlist('files')
        max_files = 10
        max_file_size = 3 * 1024 * 1024  # 3MB

        if len(files) > max_files:
            return JsonResponse({
                'error': f'Maximum {max_files} files allowed'
            }, status=400)

        for file in files:
            if file.size > max_file_size:
                continue

            # Save temporarily
            file_path = os.path.join(session_dir, 'uploads', file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)

            # Extract text immediately
            file_extension = file.name.split('.')[-1].lower()
            try:
                if file_extension == 'pdf':
                    text = extract_text_from_pdf(file_path)
                elif file_extension == 'docx':
                    text = extract_text_from_docx(file_path)
                elif file_extension == 'txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    continue

                # Log extracted text for debugging
                print(f"\n{'='*80}")
                print(f"EXTRACTED TEXT FROM {file.name}:")
                print(f"{'='*80}")
                print(text[:1000])  # Print first 1000 characters
                if len(text) > 1000:
                    print(f"... (truncated, total length: {len(text)} characters)")
                print(f"{'='*80}\n")

                # Add to session
                resume_data = {
                    'id': str(uuid.uuid4()),
                    'filename': file.name,
                    'text': text,
                    'status': 'pending'
                }
                batch['resumes'].append(resume_data)

            except Exception as e:
                print(f"Error processing {file.name}: {e}")
            finally:
                # Delete original file after text extraction
                try:
                    os.remove(file_path)
                except:
                    pass

        batch['status'] = 'ready'
        request.session.save()

        return JsonResponse({
            'success': True,
            'batch_id': batch['batch_id'],
            'resume_count': len(batch['resumes']),
            'resumes': batch['resumes']  # Return the resumes with extracted text
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Upload failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def analyze_batch(request):
    """Analyze resumes against JD with parallel processing"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            jd_text = data.get('job_description')
            resumes = data.get('resumes', [])
        else:
            # Fallback to form data for session-based approach
            batch = request.session.get('recruiter_batch')
            if not batch:
                return JsonResponse({'error': 'No batch found'}, status=404)

            jd_text = request.POST.get('job_description')
            if not jd_text:
                return JsonResponse({'error': 'Job description required'}, status=400)

            resumes = batch.get('resumes', [])

        if not jd_text:
            return JsonResponse({'error': 'Job description required'}, status=400)

        if not resumes:
            return JsonResponse({'error': 'No resumes to analyze'}, status=400)

        jd_lower = jd_text.strip().lower()
        jd_words = jd_lower.split()
        invalid_indicators = [
            len(jd_text.strip()) < 100,  # Too short
            jd_text.strip() == jd_lower,  # All lowercase
            len(set(jd_words)) < 10,  # Too few unique words
            any(word in jd_lower for word in [
                'dsadasd', 'asdfgh', 'qwerty',
                'sample text', 'placeholder text'
            ]),
            # Check if it's mostly random characters
            sum(1 for c in jd_text if c.isalnum()) / len(jd_text) < 0.7
            if jd_text else False
        ]

        if any(invalid_indicators):
            return JsonResponse({
                'error': (
                    'Invalid job description. Please provide a real job '
                    'description with specific requirements and qualifications.'
                )
            }, status=400)

        for resume in resumes:
            resume_text = (resume.get('text') or '').strip()
            if not resume_text:
                return JsonResponse({
                    'error': f"Resume text is required for {resume.get('filename', 'a file')}."
                }, status=400)

            resume_lower = resume_text.lower()
            resume_words = resume_lower.split()
            resume_invalid_indicators = [
                len(resume_text) < 100,
                resume_text == resume_lower,
                len(set(resume_words)) < 10,
                any(word in resume_lower for word in [
                    'dsadasd', 'asdfgh', 'qwerty',
                    'sample text', 'placeholder text'
                ]),
                sum(1 for c in resume_text if c.isalnum()) / len(resume_text) < 0.7
                if resume_text else False
            ]

            if any(resume_invalid_indicators):
                return JsonResponse({
                    'error': (
                        f"Invalid resume text in {resume.get('filename', 'a file')}. "
                        "Please upload a resume with real content."
                    )
                }, status=400)

        # Process resumes in parallel (max 3 at a time)
        results = []
        max_parallel = 3

        async def analyze_single_resume(resume):
            """Analyze a single resume"""
            try:
                result = await openrouter_service.analyze_resume_match(
                    resume_text=resume['text'],
                    job_description=jd_text,
                    resume_structured={}
                )
                return {
                    'resume_id': resume['id'],
                    'filename': resume['filename'],
                    'analysis': result
                }
            except Exception as e:
                return {
                    'resume_id': resume['id'],
                    'filename': resume['filename'],
                    'error': str(e)
                }

        async def process_in_chunks():
            """Process resumes in chunks with parallel execution"""
            all_results = []

            for i in range(0, len(resumes), max_parallel):
                chunk = resumes[i:i+max_parallel]

                # Create tasks for parallel processing
                tasks = [analyze_single_resume(resume) for resume in chunk]

                # Wait for all tasks in this chunk to complete
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and add valid results
                for result in chunk_results:
                    if not isinstance(result, Exception):
                        all_results.append(result)

                # Small delay between chunks to avoid overwhelming
                await asyncio.sleep(0.1)

            return all_results

        # Run the async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(process_in_chunks())
        loop.close()

        return JsonResponse({
            'success': True,
            'results': results
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Analysis failed: {str(e)}'
        }, status=500)

def get_batch_status(request):
    """Get current batch status"""
    batch = request.session.get('recruiter_batch', {})

    return JsonResponse({
        'status': batch.get('status', 'ready'),
        'resume_count': len(batch.get('resumes', [])),
        'results_count': len(batch.get('results', [])),
        'resumes': batch.get('resumes', []),
        'results': batch.get('results', [])
    })

@csrf_exempt
def clear_batch(request):
    """Clear current batch"""
    if 'recruiter_batch' in request.session:
        del request.session['recruiter_batch']
        request.session.save()

    return JsonResponse({'success': True})
