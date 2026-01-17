from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from ai.services import openrouter_service
from resumes.models import ResumeDocument
from jobs.models import JobDescription
from security.file_scanner import file_scanner
import json
import asyncio
import PyPDF2
import docx
import io
import tempfile
import os

# Try to import pdfplumber as fallback
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

def talent_dashboard(request):
    """Simple talent dashboard without login requirements"""
    return render(request, 'talent/dashboard.html')

def talent_analysis(request):
    """Talent analysis page - no login required"""
    return render(request, 'talent/analysis.html')

@csrf_exempt
@require_POST
def analyze_resume(request):
    """Handle resume analysis form submission"""
    try:
        # Get form data
        resume_id = request.POST.get('resume_id')
        job_description_id = request.POST.get('job_description_id')

        if not resume_id or not job_description_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Please select both a resume and job description'
                }, status=400)
            else:
                messages.error(request, 'Please select both a resume and job description')
                return redirect('talent:analysis')

        # Get resume and job description
        resume = get_object_or_404(ResumeDocument, id=resume_id)
        job_description = get_object_or_404(JobDescription, id=job_description_id)

        # Extract resume text
        resume_text = resume.extracted_text or ""

        # Run AI analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Get AI analysis
            ai_result = loop.run_until_complete(
                openrouter_service.analyze_resume_match(
                    resume_text=resume_text,
                    job_description=job_description.raw_text,
                    resume_structured={}
                )
            )

            # Store results in session for results page
            request.session['analysis_results'] = {
                'overall_score': ai_result.get('overall_score', 50),
                'component_scores': ai_result.get('component_scores', {}),
                'matched_requirements': ai_result.get('matched_requirements', []),
                'missing_requirements': ai_result.get('missing_requirements', []),
                'concerns': ai_result.get('concerns', []),
                'recommendations': ai_result.get('recommendations', {}),
                'confidence': ai_result.get('confidence', 50),
                'resume_id': resume_id,
                'job_description_id': job_description_id
            }

            # Redirect to results page
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('talent:analysis_results') + f'?resume_id={resume_id}&job_description_id={job_description_id}'
                })
            else:
                return redirect(reverse('talent:analysis_results') + f'?resume_id={resume_id}&job_description_id={job_description_id}')

        finally:
            loop.close()

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }, status=500)
        else:
            messages.error(request, f'Analysis failed: {str(e)}')
            return redirect('talent:analysis')

@csrf_exempt
@require_POST
def upload_resume_file(request):
    """Upload and process resume file"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'error': 'No file uploaded'
            }, status=400)

        file = request.FILES['file']
        file_extension = file.name.split('.')[-1].lower()

        # First, save file temporarily for security scanning
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            # Security scan the file
            is_safe, error_message, warnings = file_scanner.scan_file(temp_file_path, file.name)

            if not is_safe:
                return JsonResponse({
                    'error': f'Security check failed: {error_message}'
                }, status=400)

            # Log any warnings
            for warning in warnings:
                print(f"Security warning for {file.name}: {warning}")

            # Extract text based on file type
            if file_extension == 'txt':
                # Handle text files
                with open(temp_file_path, 'rb') as f:
                    text = f.read().decode('utf-8')
            elif file_extension == 'pdf':
                # Handle PDF files
                with open(temp_file_path, 'rb') as f:
                    pdf_file = io.BytesIO(f.read())
                text = extract_text_from_pdf(pdf_file)
            elif file_extension == 'docx':
                # Handle DOCX files
                with open(temp_file_path, 'rb') as f:
                    docx_file = io.BytesIO(f.read())
                text = extract_text_from_docx(docx_file)
            else:
                return JsonResponse({
                    'error': f'Unsupported file type: {file_extension}. Please use .txt, .pdf, or .docx files.'
                }, status=400)

            # Check if text extraction was successful
            if not text or text.strip() == '':
                return JsonResponse({
                    'error': 'Unable to extract text from the file. The file may be corrupted, password-protected, or scanned (image-based).'
                }, status=400)

            return JsonResponse({
                'success': True,
                'text': text,
                'filename': file.name
            })

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass

    except Exception as e:
        return JsonResponse({
            'error': f'File processing failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def analyze_resume_text(request):
    """Analyze resume text against job description without saving to DB"""
    try:
        # Get data from request
        data = json.loads(request.body)
        resume_text = data.get('resume_text', '')
        job_description = data.get('job_description', '')

        if not resume_text or not job_description:
            return JsonResponse({
                'error': 'Both resume text and job description are required'
            }, status=400)

        # Run AI analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Get AI analysis
            ai_result = loop.run_until_complete(
                openrouter_service.analyze_resume_match(
                    resume_text=resume_text,
                    job_description=job_description,
                    resume_structured={}
                )
            )

            invalid_jd_message = None
            missing_requirements = ai_result.get('missing_requirements', [])
            for item in missing_requirements:
                if isinstance(item, str) and 'No clear job description provided' in item:
                    invalid_jd_message = item
                    break

            if invalid_jd_message:
                return JsonResponse({
                    'error': invalid_jd_message
                }, status=400)

            # Extract skills from resume
            skills = loop.run_until_complete(
                openrouter_service.extract_skills_from_text(resume_text)
            )

            # Generate recommendations
            recommendations = ai_result.get('recommendations', {})

            response_data = {
                'success': True,
                'overall_score': ai_result.get('overall_score', 50),
                'component_scores': ai_result.get('component_scores', {}),
                'matched_requirements': ai_result.get('matched_requirements', []),
                'missing_requirements': ai_result.get('missing_requirements', []),
                'concerns': ai_result.get('concerns', []),
                'recommendations': recommendations,
                'confidence': ai_result.get('confidence', 50),
                'extracted_skills': skills
            }

            return JsonResponse(response_data)

        finally:
            loop.close()

    except Exception as e:
        return JsonResponse({
            'error': f'Analysis failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def improve_resume_bullets(request):
    """Improve resume bullet points based on job requirements"""
    try:
        data = json.loads(request.body)
        bullets = data.get('bullets', [])
        job_requirements = data.get('job_requirements', [])

        if not bullets:
            return JsonResponse({
                'error': 'Resume bullets are required'
            }, status=400)

        # Run AI improvement
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            improved_bullets = loop.run_until_complete(
                openrouter_service.improve_resume_bullets(bullets, job_requirements)
            )

            return JsonResponse({
                'success': True,
                'improved_bullets': improved_bullets
            })

        finally:
            loop.close()

    except Exception as e:
        return JsonResponse({
            'error': f'Improvement failed: {str(e)}'
        }, status=500)

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        # Reset file pointer to beginning
        file.seek(0)

        # First try with PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""

            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            # If we got good text, return it
            if text.strip() and len(text.strip()) > 50:
                return text.strip()
        except Exception as e:
            print(f"PyPDF2 extraction failed: {str(e)}")

        # Fallback to pdfplumber if available
        if HAS_PDFPLUMBER:
            try:
                file.seek(0)  # Reset file pointer
                with pdfplumber.open(file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

                    if text.strip() and len(text.strip()) > 50:
                        return text.strip()
            except Exception as e:
                print(f"pdfplumber extraction failed: {str(e)}")

        # If no text extracted, the PDF might be scanned/image-based
        raise Exception("No text could be extracted from this PDF. It may be a scanned document, password-protected, or contain images only.")

    except Exception as e:
        raise Exception(f"PDF processing failed: {str(e)}")

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        # Reset file pointer to beginning if it's a file-like object
        if hasattr(file, 'seek'):
            file.seek(0)
        # Read file content
        file_content = file.read() if hasattr(file, 'read') else file
        # Create document from bytes
        doc = docx.Document(io.BytesIO(file_content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise Exception(f"DOCX processing failed: {str(e)}")

def talent_suggestions(request, resume_id):
    """Show improvement suggestions for a resume"""
    # Get resume document
    resume = get_object_or_404(ResumeDocument, id=resume_id)

    # Get job description from query params
    job_description_id = request.GET.get('job_description_id')
    job_description = None
    if job_description_id:
        job_description = get_object_or_404(JobDescription, id=job_description_id)

    # Extract resume text
    resume_text = resume.extracted_text or ""

    context = {
        'resume': resume,
        'job_description': job_description,
        'resume_text': resume_text,
    }

    return render(request, 'talent/suggestions.html', context)

@csrf_exempt
@require_POST
def get_suggestions(request):
    """Get AI-powered suggestions for resume improvement"""
    try:
        data = json.loads(request.body)
        resume_text = data.get('resume_text', '')
        job_description_id = data.get('job_description_id')

        if not resume_text:
            return JsonResponse({
                'error': 'Resume text is required'
            }, status=400)

        # Get job description if provided
        job_description = None
        job_requirements = []
        if job_description_id:
            try:
                job_description = JobDescription.objects.get(id=job_description_id)
                job_requirements = job_description.requirements or []
            except JobDescription.DoesNotExist:
                pass

        # Run AI analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Extract bullet points from resume
            bullets = extract_bullet_points(resume_text)

            # Get improved bullets
            bullet_improvements = []
            if bullets and job_requirements:
                improved_bullets = loop.run_until_complete(
                    openrouter_service.improve_resume_bullets(bullets, job_requirements)
                )
                bullet_improvements = improved_bullets.get('improvements', [])

            # Extract skills
            resume_skills = loop.run_until_complete(
                openrouter_service.extract_skills_from_text(resume_text)
            )

            # Get job skills if job description exists
            job_skills = []
            if job_description:
                job_skills = job_description.skills or []

            # Analyze skill gaps
            skill_gap_analysis = analyze_skill_gaps(resume_skills, job_skills)

            # Generate content recommendations
            content_recommendations = generate_content_recommendations(
                resume_text,
                job_description.description if job_description else ""
            )

            return JsonResponse({
                'success': True,
                'bullet_improvements': bullet_improvements,
                'skill_gap_analysis': skill_gap_analysis,
                'content_recommendations': content_recommendations
            })

        finally:
            loop.close()

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to get suggestions: {str(e)}'
        }, status=500)

def extract_bullet_points(text):
    """Extract bullet points from resume text"""
    import re

    # Common bullet point patterns
    bullet_patterns = [
        r'^[•·-]\s*(.+)$',  # •, ·, or - at start
        r'^\*\s*(.+)$',    # * at start
        r'^\d+\.\s*(.+)$', # Numbered list
        r'^▪\s*(.+)$',     # Square bullet
    ]

    lines = text.split('\n')
    bullets = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in bullet_patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                bullets.append(match.group(1))
                break

    return bullets

def analyze_skill_gaps(resume_skills, job_skills):
    """Analyze skill gaps between resume and job requirements"""
    resume_skills_set = set(skill.lower() for skill in resume_skills)
    job_skills_set = set(skill.lower() for skill in job_skills)

    missing_skills = list(job_skills_set - resume_skills_set)
    matched_skills = list(resume_skills_set & job_skills_set)

    # Generate suggestions for missing skills
    suggestions = []
    for skill in missing_skills[:5]:  # Limit to top 5 missing skills
        suggestions.append({
            'skill': skill,
            'suggestion': f"Consider highlighting experience with {skill} or taking relevant courses/certifications."
        })

    return {
        'missing_skills': missing_skills,
        'matched_skills': matched_skills,
        'suggestions': suggestions
    }

def generate_content_recommendations(resume_text, job_description):
    """Generate content recommendations for resume improvement"""
    recommendations = []

    # Check for common sections
    has_summary = any('summary' in line.lower() or 'objective' in line.lower()
                      for line in resume_text.split('\n'))
    has_experience = any('experience' in line.lower() for line in resume_text.split('\n'))
    has_education = any('education' in line.lower() for line in resume_text.split('\n'))
    has_skills = any('skills' in line.lower() for line in resume_text.split('\n'))

    # Generate recommendations based on missing sections
    if not has_summary:
        recommendations.append({
            'category': 'Professional Summary',
            'suggestion': 'Add a professional summary at the beginning of your resume to highlight your key qualifications and career goals.'
        })

    if not has_experience:
        recommendations.append({
            'category': 'Work Experience',
            'suggestion': 'Ensure you have a detailed work experience section with quantifiable achievements.'
        })

    if not has_education:
        recommendations.append({
            'category': 'Education',
            'suggestion': 'Include your education background with degrees, institutions, and graduation dates.'
        })

    if not has_skills:
        recommendations.append({
            'category': 'Skills Section',
            'suggestion': 'Add a dedicated skills section to showcase your technical and soft skills.'
        })

    # Check for quantifiable achievements
    has_metrics = any('$' in line or '%' in line or re.search(r'\d+', line)
                     for line in resume_text.split('\n'))

    if not has_metrics:
        recommendations.append({
            'category': 'Quantifiable Achievements',
            'suggestion': 'Include specific metrics and numbers to demonstrate the impact of your work (e.g., "Increased sales by 25%").'
        })

    # Check resume length
    word_count = len(resume_text.split())
    if word_count < 300:
        recommendations.append({
            'category': 'Resume Length',
            'suggestion': 'Your resume appears too short. Consider adding more detail about your experiences and achievements.'
        })
    elif word_count > 600:
        recommendations.append({
            'category': 'Resume Length',
            'suggestion': 'Your resume is quite long. Consider condensing content to focus on the most relevant information.'
        })

    return recommendations
