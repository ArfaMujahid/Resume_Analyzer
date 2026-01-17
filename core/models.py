from django.db import models
from django.utils import timezone

class SiteSettings(models.Model):
    """Global site settings"""
    site_name = models.CharField(max_length=100, default="Resume Analyzer")
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    max_file_size = models.IntegerField(default=20)  # MB
    supported_file_types = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name

class AuditLog(models.Model):
    """Track important actions for compliance"""
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
