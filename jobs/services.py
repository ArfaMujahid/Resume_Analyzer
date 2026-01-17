from typing import Dict, List, Any, Optional
from django.db import transaction
from django.utils import timezone

from ai import openrouter_service, ScoringEngine
from .models import JobDescription, AnalysisRun, MatchResult


class JobDescriptionService:
    """Service for managing job descriptions"""

    @staticmethod
    def create_job_description(owner, title: str, raw_text: str,
                               company: str = None, location: str = None,
                               salary_range: str = None,
                               min_years_experience: int = None,
                               degree_requirements: str = None) -> JobDescription:
        """Create a new job description with AI structuring"""
        try:
            # Create basic job description
            job = JobDescription.objects.create(
                owner=owner,
                title=title,
                company=company,
                location=location,
                raw_text=raw_text,
                salary_range=salary_range,
                min_years_experience=min_years_experience,
                degree_requirements=degree_requirements,
                structured_json={},
                requirements_required=[],
                requirements_preferred=[],
                responsibilities=[],
                skills_required=[],
                skills_preferred=[],
                embedding_refs=[]
            )

            # Structure the job description using AI
            structured_data = openrouter_service._structure_job_description(raw_text)
            if structured_data:
                job.structured_json = structured_data
                job.requirements_required = structured_data.get('requirements_required', [])
                job.requirements_preferred = structured_data.get('requirements_preferred', [])
                job.responsibilities = structured_data.get('responsibilities', [])
                job.skills_required = structured_data.get('skills_required', [])
                job.skills_preferred = structured_data.get('skills_preferred', [])
                job.save()

            return job

        except Exception as e:
            print(f"Error creating job description: {str(e)}")
            raise

    @staticmethod
    async def analyze_job_description(job_description: JobDescription) -> Dict[str, Any]:
        """Analyze job description and extract requirements"""
        try:
            # Use AI to structure the job description
            structured_data = openrouter_service._structure_job_description(job_description.raw_text)

            if structured_data:
                job_description.structured_json = structured_data
                job_description.requirements_required = structured_data.get('requirements_required', [])
                job_description.requirements_preferred = structured_data.get('requirements_preferred', [])
                job_description.responsibilities = structured_data.get('responsibilities', [])
                job_description.skills_required = structured_data.get('skills_required', [])
                job_description.skills_preferred = structured_data.get('skills_preferred', [])
                job_description.save()

            return structured_data

        except Exception as e:
            print(f"Error analyzing job description: {str(e)}")
            return {}

    @staticmethod
    def extract_skills_from_text(text: str) -> List[str]:
        """Extract skills from job description text"""
        try:
            # Use AI to extract skills
            skills = openrouter_service._extract_skills_from_text(text)
            return skills
        except Exception as e:
            print(f"Error extracting skills: {str(e)}")
            return []


class AnalysisService:
    """Service for running resume analysis"""

    @staticmethod
    async def run_analysis(actor, actor_role: str, resume_ids: List[str],
                         job_description_id: str) -> AnalysisRun:
        """Run analysis on resumes against job description"""
        try:
            # Create analysis run
            analysis = AnalysisRun.objects.create(
                actor=actor,
                actor_role=actor_role,
                resume_ids=resume_ids,
                job_description_id=job_description_id,
                config_version='v1.0',
                status='running'
            )

            # Get job description
            job_description = JobDescription.objects.get(id=job_description_id)

            # Process each resume
            results = []
            for resume_id in resume_ids:
                try:
                    # Calculate match score
                    score_data = await ScoringEngine.calculate_match_score(
                        resume_id, job_description_id
                    )

                    # Create match result
                    match_result = MatchResult.objects.create(
                        analysis_run=analysis,
                        resume_id=resume_id,
                        overall_score=score_data['overall_score'],
                        semantic_similarity=score_data['component_scores']['semantic_similarity'],
                        skills_match=score_data['component_scores']['skills_match'],
                        experience_seniority=score_data['component_scores']['experience_fit'],
                        education_certs=score_data['component_scores']['education_match'],
                        penalties=score_data['component_scores']['penalties'],
                        required_skills_coverage_pct=0,  # TODO: Calculate
                        preferred_skills_coverage_pct=0,  # TODO: Calculate
                        relevant_years_estimate=0,  # TODO: Calculate
                        title_level_match='',  # TODO: Calculate
                        evidence=score_data['evidence'],
                        recommendations=score_data['recommendations'],
                        confidence=score_data['confidence']
                    )

                    results.append(match_result)

                except Exception as e:
                    print(f"Error analyzing resume {resume_id}: {str(e)}")
                    continue

            # Update analysis status
            analysis.status = 'complete'
            analysis.results_ref = f"results_{analysis.id}"
            analysis.save()

            return analysis

        except Exception as e:
            print(f"Error running analysis: {str(e)}")
            analysis.status = 'failed'
            analysis.save()
            raise

    @staticmethod
    def get_analysis_results(analysis_run_id: str) -> List[MatchResult]:
        """Get results for an analysis run"""
        try:
            return MatchResult.objects.filter(
                analysis_run_id=analysis_run_id
            ).order_by('-overall_score')
        except Exception as e:
            print(f"Error getting analysis results: {str(e)}")
            return []

    @staticmethod
    def get_candidate_ranking(job_description_id: str, resume_ids: List[str] = None) -> List[Dict]:
        """Get ranked list of candidates for a job description"""
        try:
            if not resume_ids:
                # Get all resumes for this job description
                from resumes.models import ResumeDocument
                resume_ids = ResumeDocument.objects.filter(
                    status='parsed'
                ).values_list('id', flat=True)

            # Get all match results for this job description
            matches = MatchResult.objects.filter(
                resume_id__in=resume_ids,
                analysis_run__job_description_id=job_description_id
            ).order_by('-overall_score')

            # Format results
            results = []
            for match in matches:
                results.append({
                    'resume_id': match.resume_id,
                    'overall_score': match.overall_score,
                    'component_scores': {
                        'skills_match': match.skills_match,
                        'experience_fit': match.experience_seniority,
                        'education_certs': match.education_certs,
                        'semantic_similarity': match.semantic_similarity
                    },
                    'evidence': match.evidence,
                    'recommendations': match.recommendations,
                    'confidence': match.confidence
                })

            return results

        except Exception as e:
            print(f"Error getting candidate ranking: {str(e)}")
            return []


class RecommendationService:
    """Service for generating improvement recommendations"""

    @staticmethod
    async def generate_resume_improvements(resume_id: str, job_description_id: str) -> Dict[str, Any]:
        """Generate improvement suggestions for a resume"""
        try:
            from resumes.models import ResumeDocument, ParsedResume
            from jobs.models import JobDescription

            # Get resume and job description
            resume = ResumeDocument.objects.get(id=resume_id)
            jd = JobDescription.objects.get(id=job_description_id)
            parsed_resume = ParsedResume.objects.get(resume=resume)

            # Get current scores
            current_scores = await ScoringEngine.calculate_match_score(
                resume_id, job_description_id
            )

            # Generate improvements using AI
            improvements = await openrouter_service.improve_resume_bullets(
                parsed_resume.employment_history[0].get('bullets', []) if parsed_resume.employment_history else [],
                jd.requirements_required + jd.skills_required
            )

            # Create comprehensive recommendations
            recommendations = {
                "current_score": current_scores['overall_score'],
                "component_scores": current_scores['component_scores'],
                "missing_requirements": current_scores['evidence']['missing_requirements'],
                "weak_areas": current_scores['evidence']['concerns'],
                "suggestions": {
                    "skills": RecommendationService._get_skills_suggestions(
                        parsed_resume.skills_normalized,
                        jd.skills_required + jd.skills_preferred
                    ),
                    "bullets": improvements,
                    "structure": RecommendationService._get_structure_suggestions(
                        parsed_resume.quality_flags
                    )
                },
                "estimated_improvement": RecommendationService._estimate_improvement(
                    current_scores, improvements
                )
            }

            return recommendations

        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return {}

    @staticmethod
    def _get_skills_suggestions(resume_skills: List[str], required_skills: List[str]) -> List[str]:
        """Get skills improvement suggestions"""
        suggestions = []
        required_lower = [skill.lower() for skill in required_skills]
        resume_lower = [skill.lower() for skill in resume_skills]

        for skill in required_lower:
            if skill not in resume_lower:
                suggestions.append(f"Add '{skill}' to your skills section")
                # Look for similar skills
                for resume_skill in resume_lower:
                    if skill in resume_skill or resume_skill in skill:
                        suggestions.append(f"Consider using '{skill}' instead of '{resume_skill}'")
                        break

        return suggestions

    @staticmethod
    def _get_structure_suggestions(quality_flags: Dict) -> List[str]:
        """Get structure improvement suggestions"""
        suggestions = []
        flags = quality_flags.get('flags', {})

        if flags.get('missing_summary'):
            suggestions.append("Add a professional summary at the top of your resume")
        if flags.get('missing_dates'):
            suggestions.append("Include dates for all work experience")
        if flags.get('too_short'):
            suggestions.append("Add more detail to your experience descriptions")
        if flags.get('missing_email'):
            suggestions.append("Include your email address in contact information")

        return suggestions

    @staticmethod
    def _estimate_improvement(current_scores: Dict, improvements: List) -> int:
        """Estimate potential improvement score"""
        base_score = current_scores['overall_score']

        # Simple estimation - could be more sophisticated
        if improvements:
            return min(100, base_score + 15)  # Assume 15 point improvement
        return base_score