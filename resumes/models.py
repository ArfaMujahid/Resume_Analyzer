from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class ResumeDocument(models.Model):
    """Resume document uploaded by users"""
    SOURCE_CHOICES = [
        ('talent_upload', 'Talent Upload'),
        ('recruiter_batch_upload', 'Recruiter Batch Upload'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('parsing', 'Parsing'),
        ('parsed', 'Parsed'),
        ('failed', 'Failed'),
        ('deleted', 'Deleted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    source_type = models.CharField(max_length=30, choices=SOURCE_CHOICES)

    # File information
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # pdf, doc, docx, txt
    file_size_bytes = models.IntegerField()
    checksum_hash = models.CharField(max_length=64)
    storage_ref = models.CharField(max_length=500)  # S3 key or local path

    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    parsing_error = models.TextField(blank=True, null=True)

    # TTL for recruiter uploads
    ttl_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resume Document"
        verbose_name_plural = "Resume Documents"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['ttl_expires_at']),
        ]

    def __str__(self):
        return f"{self.original_filename} - {self.owner.email}"

    @property
    def is_expired(self):
        if self.ttl_expires_at:
            return timezone.now() > self.ttl_expires_at
        return False

class ParsedResume(models.Model):
    """Structured data extracted from resume"""
    EXTRACTION_CHOICES = [
        ('text_extract', 'Text Extract'),
        ('ocr_fallback', 'OCR Fallback'),
    ]

    resume = models.OneToOneField(ResumeDocument, on_delete=models.CASCADE, related_name='parsed_data')
    extraction_method = models.CharField(max_length=20, choices=EXTRACTION_CHOICES)

    # Raw text (temporary storage)
    raw_text = models.TextField(blank=True, null=True)

    # Structured JSON
    structured_json = models.JSONField(default=dict)
    section_index = models.JSONField(default=dict)  # section -> offsets/chunk ids

    # Extracted entities
    skills_normalized = models.JSONField(default=list)
    titles_normalized = models.JSONField(default=list)
    companies = models.JSONField(default=list)
    employment_history = models.JSONField(default=list)
    education = models.JSONField(default=list)
    certifications = models.JSONField(default=list)

    # Quality flags
    quality_flags = models.JSONField(default=dict)

    # Embedding references
    embedding_refs = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parsed Resume"
        verbose_name_plural = "Parsed Resumes"

    def __str__(self):
        return f"Parsed: {self.resume.original_filename}"

class ResumeChunk(models.Model):
    """Chunk of resume text for embedding and similarity search"""
    resume = models.ForeignKey(ResumeDocument, on_delete=models.CASCADE, related_name='chunks')
    chunk_id = models.CharField(max_length=50)
    section = models.CharField(max_length=50)  # experience, skills, education, projects

    text = models.TextField()
    start_offset = models.IntegerField()
    end_offset = models.IntegerField()
    page_number = models.IntegerField(null=True, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict)

    # Embedding vector (stored as array)
    embedding_vector = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resume Chunk"
        verbose_name_plural = "Resume Chunks"
        unique_together = ['resume', 'chunk_id']
        indexes = [
            models.Index(fields=['resume', 'section']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_id} - {self.resume.original_filename}"
