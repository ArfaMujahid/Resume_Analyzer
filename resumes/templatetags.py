from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def quality_color(score):
    """Return Bootstrap color class based on quality score"""
    if score >= 80:
        return 'success'
    elif score >= 60:
        return 'info'
    elif score >= 40:
        return 'warning'
    else:
        return 'danger'


@register.filter
def score_class(score):
    """Return CSS class for score display"""
    if score >= 80:
        return 'score-excellent'
    elif score >= 60:
        return 'score-good'
    elif score >= 40:
        return 'score-average'
    else:
        return 'score-poor'