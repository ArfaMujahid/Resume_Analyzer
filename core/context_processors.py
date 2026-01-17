from .models import SiteSettings

def site_context(request):
    """Add site-wide context variables to all templates"""
    return {
        'site_name': 'Resume Analyzer',
        'app_version': '1.0.0',
        'support_email': 'support@resumeanalyzer.com',
    }