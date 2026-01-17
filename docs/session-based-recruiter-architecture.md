# Session-Based Recruiter Architecture (No Database)

## Overview
This document outlines the architecture for converting the recruiter functionality from a database-driven, user-login system to a session-based approach that requires no authentication and no persistent database storage.

## 1. **No Database - Pure Session/File System**
- All data stored in Django session or temporary files
- Auto-cleanup when session expires
- No persistent storage needed

## 2. **Temporary Storage Strategy**
```
Session Flow:
1. Upload → Store in /tmp/session_{session_id}/
2. Analysis → Process and store results in session
3. Auto-cleanup → Session expiration deletes all
```

## 3. **LLM Context Management**
```
Batch Processing Strategy:
- Process 5 resumes at a time (context limit)
- Store results in session memory
- Stream results to frontend
- Show real-time progress
```

## 4. **Front-end Limitations**
```
Hard Limits:
- Max resumes per batch: 10 (reduced for memory)
- Max file size: 3MB each
- Max total size: 20MB per batch
- Session timeout: 2 hours
```

## 5. **Multiple File Types Handling**
```
File Type Processing:
1. Upload → Detect type
2. Convert → Extract text immediately
3. Store → Only text in session, delete original file
4. Standardize → All as plain text for LLM
```

## 6. **Reusing Talent Analysis Module**
```
Direct Reuse:
- Same analyze_resume_match function
- Called in loop for each resume
- Results collected in session
- No database storage
```

## Detailed Architecture

### Session Data Structure
```python
# Django session data
request.session['recruiter_batch'] = {
    'batch_id': str(uuid.uuid4()),
    'created_at': timestamp,
    'job_description': 'JD text...',
    'resumes': [
        {
            'id': str(uuid.uuid4()),
            'filename': 'resume1.pdf',
            'text': 'Extracted resume text...',
            'status': 'pending'  # pending, processing, completed, error
        }
    ],
    'results': [
        {
            'resume_id': 'uuid',
            'analysis': {  # Same structure as talent results
                'overall_score': 85,
                'component_scores': {...},
                'matched_requirements': [...],
                'missing_requirements': [...],
                'concerns': [...],
                'recommendations': {...}
            }
        }
    ],
    'status': 'uploading'  # uploading, ready, processing, completed
}
```

### File Storage (Temporary)
```python
# /tmp/recruiter_sessions/{session_id}/
# ├── uploads/
# │   ├── resume1.pdf
# │   ├── resume2.docx
# │   └── ...
# └── processed/
#     ├── resume1.txt
#     ├── resume2.txt
#     └── ...

# Auto-cleanup middleware
class SessionCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Clean up old sessions
        if hasattr(request, 'session'):
            session_age = time.time() - request.session.get('created_at', 0)
            if session_age > 7200:  # 2 hours
                self.cleanup_session(request.session.session_key)

        return response

    def cleanup_session(self, session_id):
        import shutil
        session_dir = f'/tmp/recruiter_sessions/{session_id}'
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
```

### Processing Flow
```python
# recruiter/views.py
@csrf_exempt
def upload_batch(request):
    """Upload multiple resumes for batch processing"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

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
    for file in files:
        # Validate file
        if file.size > 3 * 1024 * 1024:  # 3MB limit
            continue

        # Save temporarily
        file_path = os.path.join(session_dir, 'uploads', file.name)
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Extract text immediately
        text = extract_text_from_file(file_path, file.name)

        # Add to session
        resume_data = {
            'id': str(uuid.uuid4()),
            'filename': file.name,
            'text': text,
            'status': 'pending'
        }
        batch['resumes'].append(resume_data)

        # Delete original file after text extraction
        os.remove(file_path)

    batch['status'] = 'ready'
    request.session.save()

    return JsonResponse({
        'success': True,
        'batch_id': batch['batch_id'],
        'resume_count': len(batch['resumes'])
    })

@csrf_exempt
def analyze_batch(request):
    """Analyze all resumes in batch against JD"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    batch = request.session.get('recruiter_batch')
    if not batch:
        return JsonResponse({'error': 'No batch found'}, status=404)

    jd_text = request.POST.get('job_description')
    if not jd_text:
        return JsonResponse({'error': 'Job description required'}, status=400)

    batch['job_description'] = jd_text
    batch['status'] = 'processing'
    request.session.save()

    # Process resumes in chunks
    results = []
    chunk_size = 5

    for i in range(0, len(batch['resumes']), chunk_size):
        chunk = batch['resumes'][i:i+chunk_size]

        for resume in chunk:
            try:
                # Update status
                resume['status'] = 'processing'
                request.session.save()

                # Reuse talent's analyzer
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    openrouter_service.analyze_resume_match(
                        resume_text=resume['text'],
                        job_description=jd_text,
                        resume_structured={}
                    )
                )

                # Store result
                results.append({
                    'resume_id': resume['id'],
                    'filename': resume['filename'],
                    'analysis': result
                })

                resume['status'] = 'completed'
                loop.close()

            except Exception as e:
                resume['status'] = 'error'
                resume['error'] = str(e)

        # Update session after each chunk
        batch['results'] = results
        request.session.save()

    batch['status'] = 'completed'
    request.session.save()

    return JsonResponse({
        'success': True,
        'results': results
    })
```

### Front-end Implementation
```javascript
// recruiter-batch.js
class RecruiterBatchManager {
    constructor() {
        this.maxResumes = 10;
        this.maxFileSize = 3 * 1024 * 1024; // 3MB
        this.currentBatch = null;
    }

    async uploadResumes(files) {
        // Validate
        if (files.length > this.maxResumes) {
            throw new Error(`Maximum ${this.maxResumes} resumes allowed`);
        }

        const formData = new FormData();
        files.forEach(file => {
            if (file.size > this.maxFileSize) {
                throw new Error(`File ${file.name} exceeds 3MB limit`);
            }
            formData.append('files', file);
        });

        const response = await fetch('/recruiter/api/upload/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        return await response.json();
    }

    async analyzeBatch(jobDescription) {
        const formData = new FormData();
        formData.append('job_description', jobDescription);

        const response = await fetch('/recruiter/api/analyze/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        return await response.json();
    }

    async getBatchStatus() {
        const response = await fetch('/recruiter/api/status/');
        return await response.json();
    }
}
```

### URL Configuration
```python
# recruiter/urls.py
urlpatterns = [
    path('', views.RecruiterDashboardView.as_view(), name='dashboard'),
    path('api/upload/', views.upload_batch, name='upload_batch'),
    path('api/analyze/', views.analyze_batch, name='analyze_batch'),
    path('api/status/', views.get_batch_status, name='batch_status'),
]
```

## Benefits
1. **Zero database dependency**
2. **True session isolation**
3. **Auto-cleanup on session expiry**
4. **Memory efficient** (process in chunks)
5. **Reuses all talent code**
6. **Simple deployment**

## Limitations
1. **Session size limits** (Django default ~64KB)
2. **No persistence** (lost on session expiry)
3. **Memory constraints** (all data in session)
4. **No audit trail** (no history)

## Mitigations
- Store only text and results in session
- Delete files immediately after text extraction
- Use chunked processing
- Clear session on completion

## Implementation Order
1. Create session-based views
2. Implement file upload with text extraction
3. Add batch processing with chunking
4. Update front-end for progress tracking
5. Add session cleanup middleware
6. Test with various file types and sizes
7. Optimize memory usage

## Security Considerations
- File type validation
- Size limits enforcement
- Session timeout implementation
- Temporary file cleanup
- Input sanitization for job descriptions