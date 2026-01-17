from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class JobDescription(models.Model):
    """Job description for matching"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_descriptions')

    # Basic info
    title = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    # Raw text
    raw_text = models.TextField()

    # Structured JSON
    structured_json = models.JSONField(default=dict)
    requirements_required = models.JSONField(default=list)
    requirements_preferred = models.JSONField(default=list)
    responsibilities = models.JSONField(default=list)
    skills_required = models.JSONField(default=list)
    skills_preferred = models.JSONField(default=list)

    # Optional constraints
    min_years_experience = models.IntegerField(null=True, blank=True)
    degree_requirements = models.CharField(max_length=100, blank=True, null=True)
    salary_range = models.CharField(max_length=100, blank=True, null=True)

    # Embedding references
    embedding_refs = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job Description"
        verbose_name_plural = "Job Descriptions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.company or 'No Company'}"

class RecruiterBatch(models.Model):
    """Batch of resumes uploaded by recruiter"""
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
        ('deleted', 'Deleted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='batches')
    organization = models.CharField(max_length=100, blank=True, null=True)

    # Job description for this batch
    job_description = models.ForeignKey(JobDescription, on_delete=models.SET_NULL, null=True, blank=True)

    # Resume references
    resume_ids = models.JSONField(default=list)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    processing_error = models.TextField(blank=True, null=True)

    # TTL - required for recruiter data
    ttl_expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recruiter Batch"
        verbose_name_plural = "Recruiter Batches"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['ttl_expires_at']),
        ]

    def __str__(self):
        return f"Batch {self.id} - {self.owner.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.ttl_expires_at

    @property
    def resume_count(self):
        return len(self.resume_ids) if self.resume_ids else 0

class AnalysisRun(models.Model):
    """Analysis run for resume matching"""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('complete', 'Complete'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    actor_role = models.CharField(max_length=20)

    # References
    resume_ids = models.JSONField(default=list)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)

    # Configuration
    config_version = models.CharField(max_length=20)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    results_ref = models.CharField(max_length=500, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    # Metrics
    duration_ms = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor', 'status']),
            models.Index(fields=['job_description']),
        ]

    def __str__(self):
        return f"Analysis {self.id} - {self.actor.email}"

class MatchResult(models.Model):
    """Result of resume matching analysis"""
    analysis_run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE, related_name='match_results')
    resume = models.ForeignKey('resumes.ResumeDocument', on_delete=models.CASCADE)

    # Scores
    overall_score = models.IntegerField()
    semantic_similarity = models.IntegerField(default=0)
    skills_match = models.IntegerField(default=0)
    experience_seniority = models.IntegerField(default=0)
    education_certs = models.IntegerField(default=0)
    penalties = models.IntegerField(default=0)

    # Derived signals
    required_skills_coverage_pct = models.FloatField(default=0)
    preferred_skills_coverage_pct = models.FloatField(default=0)
    relevant_years_estimate = models.FloatField(default=0)
    title_level_match = models.CharField(max_length=50, blank=True, null=True)

    # Evidence and recommendations
    evidence = models.JSONField(default=dict)
    recommendations = models.JSONField(default=dict)
    confidence = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Match Result"
        verbose_name_plural = "Match Results"
        unique_together = ['analysis_run', 'resume']
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['analysis_run', 'overall_score']),
            models.Index(fields=['resume']),
        ]

    def __str__(self):
        return f"Match {self.overall_score}% - {self.resume.original_filename}"
