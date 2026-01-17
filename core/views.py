from django.shortcuts import render


def home(request):
    highlights = [
        {
            "title": "Evidence-first scoring",
            "detail": "Every match is tied to a snippet with confidence and source.",
        },
        {
            "title": "AI-Analysis",
            "detail": "Only top evidence goes to the LLM, never the full resume.",
        },
        {
            "title": "Fairness guardrails",
            "detail": "Protected attributes are excluded from analysis by design.",
        },
        {
            "title": "Batch-ready recruiting",
            "detail": "Rank multiple candidates with transparent tie-breakers.",
        },
    ]
    return render(request, "home.html", {"highlights": highlights})


def talent_dashboard(request):
    resumes = [
        {
            "name": "Amina-Khan-Resume.pdf",
            "status": "Parsed",
            "updated": "2 hours ago",
            "score": 86,
        },
        {
            "name": "Amina-Khan-Resume-2024.docx",
            "status": "Parsing",
            "updated": "Just now",
            "score": None,
        },
        {
            "name": "Amina-Portfolio-Resume.pdf",
            "status": "Parsed",
            "updated": "3 days ago",
            "score": 78,
        },
    ]
    analyses = [
        {
            "role": "Product Designer",
            "company": "Pollen Labs",
            "score": 82,
            "status": "Complete",
            "date": "Today",
        },
        {
            "role": "UX Researcher",
            "company": "Brightline",
            "score": 74,
            "status": "Complete",
            "date": "Yesterday",
        },
        {
            "role": "Design Lead",
            "company": "Nimbus Health",
            "score": None,
            "status": "Queued",
            "date": "Yesterday",
        },
    ]
    return render(
        request,
        "talent_dashboard.html",
        {
            "resumes": resumes,
            "analyses": analyses,
        },
    )


def talent_analysis(request):
    steps = [
        {"label": "Resume", "status": "complete"},
        {"label": "Job Description", "status": "active"},
        {"label": "Results", "status": "upcoming"},
    ]
    return render(request, "talent_analysis.html", {"steps": steps})


def talent_results(request):
    component_scores = [
        {"label": "Semantic similarity", "score": 34, "max": 40, "percent": 85},
        {"label": "Skills match", "score": 20, "max": 25, "percent": 80},
        {"label": "Experience fit", "score": 16, "max": 20, "percent": 80},
        {"label": "Education and certs", "score": 8, "max": 10, "percent": 80},
    ]
    matches = [
        {
            "jd": "Lead user research sessions and synthesize insights.",
            "evidence": [
                "Ran 18 moderated sessions across three product lines.",
                "Created insight reports that informed roadmap planning.",
            ],
            "score": 0.91,
        },
        {
            "jd": "Translate findings into product strategy with cross-functional teams.",
            "evidence": [
                "Facilitated workshops with PMs and engineers.",
                "Defined success metrics for new onboarding flow.",
            ],
            "score": 0.84,
        },
        {
            "jd": "Build and maintain a mixed-method research program.",
            "evidence": [
                "Owned quarterly research roadmap and recruiting ops.",
                "Combined surveys, diary studies, and usability tests.",
            ],
            "score": 0.79,
        },
    ]
    missing = [
        "Experience with healthcare or regulated industries.",
        "Advanced SQL for behavioral analysis.",
        "Certification: Human Factors or CX specialization.",
    ]
    recommendations = [
        "Surface your SQL projects in the skills section and in recent bullets.",
        "Add a short line in your summary about regulated domain exposure.",
        "Clarify research ops impact using one quantified outcome.",
    ]
    return render(
        request,
        "talent_results.html",
        {
            "score": 82,
            "confidence": 86,
            "component_scores": component_scores,
            "matches": matches,
            "missing": missing,
            "recommendations": recommendations,
        },
    )


def recruiter_dashboard(request):
    batches = [
        {
            "id": "nimbus-ux-042",
            "role": "Senior UX Researcher",
            "resumes": 42,
            "status": "Ready",
            "ttl": "12 days left",
        },
        {
            "id": "pulse-pm-018",
            "role": "Product Manager",
            "resumes": 18,
            "status": "Processing",
            "ttl": "6 days left",
        },
        {
            "id": "atelier-ds-007",
            "role": "Data Scientist",
            "resumes": 7,
            "status": "Draft",
            "ttl": "29 days left",
        },
    ]
    return render(request, "recruiter_dashboard.html", {"batches": batches})
