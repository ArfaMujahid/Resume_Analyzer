from typing import Dict, List, Any, Optional
import numpy as np
from django.db.models import Avg, Count
from .services import openrouter_service

from resumes.models import ResumeChunk
from jobs.models import JobDescription


class ScoringEngine:
    """Engine for calculating match scores between resumes and job descriptions"""

    @staticmethod
    async def calculate_match_score(resume_id: str, job_description_id: str) -> Dict[str, Any]:
        """
        Calculate comprehensive match score between resume and job description

        Args:
            resume_id: Resume document ID
            job_description_id: Job description ID

        Returns:
            Dictionary with all score components
        """
        try:
            # Get resume and job description
            from resumes.models import ResumeDocument, ParsedResume
            from jobs.models import JobDescription

            resume = ResumeDocument.objects.get(id=resume_id)
            jd = JobDescription.objects.get(id=job_description_id)

            # Get parsed data
            parsed_resume = ParsedResume.objects.get(resume=resume)

            # Calculate different score components
            scores = {
                "skills_match": await ScoringEngine._calculate_skills_score(
                    parsed_resume.skills_normalized, jd.skills_required, jd.skills_preferred
                ),
                "experience_fit": await ScoringEngine._calculate_experience_score(
                    parsed_resume.employment_history, jd.min_years_experience
                ),
                "education_match": await ScoringEngine._calculate_education_score(
                    parsed_resume.education, jd.degree_requirements
                ),
                "semantic_similarity": await ScoringEngine._calculate_semantic_score(
                    parsed_resume.raw_text, jd.raw_text
                ),
                "penalties": await ScoringEngine._calculate_penalties(
                    parsed_resume.quality_flags
                )
            }

            # Calculate overall score
            overall_score = ScoringEngine._calculate_overall_score(scores)

            # Generate evidence and recommendations
            evidence = await ScoringEngine._generate_evidence(
                parsed_resume, jd, scores
            )

            recommendations = await ScoringEngine._generate_recommendations(
                parsed_resume, jd, scores
            )

            return {
                "overall_score": overall_score,
                "component_scores": scores,
                "evidence": evidence,
                "recommendations": recommendations,
                "confidence": ScoringEngine._calculate_confidence(scores)
            }

        except Exception as e:
            print(f"Scoring error: {str(e)}")
            return ScoringEngine._get_fallback_scores()

    @staticmethod
    async def _calculate_skills_score(resume_skills: List[str], required_skills: List[str],
                                      preferred_skills: List[str]) -> int:
        """Calculate skills match score (0-25)"""
        if not resume_skills:
            return 0

        resume_skills_lower = [skill.lower() for skill in resume_skills]
        required_skills_lower = [skill.lower() for skill in required_skills]
        preferred_skills_lower = [skill.lower() for skill in preferred_skills]

        # Calculate required skills coverage
        required_matches = sum(1 for skill in required_skills_lower if skill in resume_skills_lower)
        required_score = (required_matches / len(required_skills) * 15) if required_skills else 0

        # Calculate preferred skills coverage
        preferred_matches = sum(1 for skill in preferred_skills_lower if skill in resume_skills_lower)
        preferred_score = (preferred_matches / len(preferred_skills) * 10) if preferred_skills else 0

        return min(25, int(required_score + preferred_score))

    @staticmethod
    async def _calculate_experience_score(employment_history: List[Dict], min_years: Optional[int]) -> int:
        """Calculate experience fit score (0-20)"""
        if not employment_history:
            return 0

        total_years = 0
        current_level = 0

        for job in employment_history:
            # Parse years from employment
            years = ScoringEngine._parse_years_from_job(job)
            total_years += years

            # Determine seniority level
            level = ScoringEngine._determine_seniority_level(job.get('title', ''))
            current_level = max(current_level, level)

        # Score based on years of experience
        years_score = min(10, int(total_years * 2))  # 5 years = 10 points max

        # Score based on seniority level
        level_scores = {'intern': 2, 'junior': 5, 'mid': 8, 'senior': 10, 'executive': 10}
        level_score = level_scores.get(current_level, 5)

        # Check minimum requirement
        if min_years and total_years < min_years:
            level_score = max(0, level_score - 5)

        return min(20, int(years_score + level_score))

    @staticmethod
    async def _calculate_education_score(education: List[Dict], degree_requirements: Optional[str]) -> int:
        """Calculate education match score (0-10)"""
        if not education:
            return 0

        score = 0

        # Check for degree requirements
        if degree_requirements:
            degree_requirements_lower = degree_requirements.lower()
            for edu in education:
                degree = edu.get('degree', '').lower()
                if degree_requirements_lower in degree:
                    score += 8
                    break
                elif 'bachelor' in degree_requirements_lower and 'bachelor' in degree:
                    score += 6
                elif 'master' in degree_requirements_lower and 'master' in degree:
                    score += 7
                elif 'phd' in degree_requirements_lower and 'phd' in degree:
                    score += 10

        # Bonus for multiple degrees
        if len(education) > 1:
            score += 2

        return min(10, score)

    @staticmethod
    async def _calculate_semantic_score(resume_text: str, jd_text: str) -> int:
        """Calculate semantic similarity score (0-40)"""
        try:
            similarity = await openrouter_service.calculate_similarity(resume_text, jd_text)
            return int(similarity * 40)
        except:
            return 20  # Fallback score

    @staticmethod
    async def _calculate_penalties(quality_flags: Dict) -> int:
        """Calculate penalties based on quality issues (0-10)"""
        penalties = 0

        if not quality_flags:
            return 0

        flags = quality_flags.get('flags', {})

        # Penalty for missing sections
        if flags.get('missing_experience'):
            penalties += 3
        if flags.get('missing_education'):
            penalties += 2
        if flags.get('missing_skills'):
            penalties += 2

        # Penalty for quality issues
        if flags.get('too_short'):
            penalties += 2
        if flags.get('too_long'):
            penalties += 1
        if flags.get('missing_email'):
            penalties += 1

        return min(10, penalties)

    @staticmethod
    def _calculate_overall_score(scores: Dict[str, int]) -> int:
        """Calculate overall score from components"""
        overall = (
            scores.get('skills_match', 0) +
            scores.get('experience_fit', 0) +
            scores.get('education_match', 0) +
            scores.get('semantic_similarity', 0) -
            scores.get('penalties', 0)
        )
        return max(0, min(100, overall))

    @staticmethod
    async def _generate_evidence(parsed_resume, job_description, scores: Dict) -> Dict:
        """Generate evidence for matched requirements"""
        evidence = {
            "matched_requirements": [],
            "missing_requirements": [],
            "concerns": []
        }

        # Skills evidence
        resume_skills = [skill.lower() for skill in parsed_resume.skills_normalized]
        required_skills = [skill.lower() for skill in job_description.skills_required]

        for skill in required_skills:
            if skill in resume_skills:
                evidence["matched_requirements"].append({
                    "jd_text": skill,
                    "resume_snippets": [f"Proficient in {skill}"],
                    "similarity_score": 1.0
                })
            else:
                evidence["missing_requirements"].append(skill)

        # Experience evidence
        if parsed_resume.employment_history:
            for job in parsed_resume.employment_history[:3]:  # Top 3 jobs
                evidence["matched_requirements"].append({
                    "jd_text": f"Experience at {job.get('company', 'Unknown')}",
                    "resume_snippets": [
                        f"{job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}",
                        f"{job.get('dates', 'Unknown')}"
                    ],
                    "similarity_score": 0.8
                })

        # Concerns
        quality_flags = parsed_resume.quality_flags.get('flags', {})
        if quality_flags.get('too_short'):
            evidence["concerns"].append("Resume appears to be too short")
        if quality_flags.get('missing_dates'):
            evidence["concerns"].append("Missing dates in employment history")

        return evidence

    @staticmethod
    async def _generate_recommendations(parsed_resume, job_description, scores: Dict) -> Dict:
        """Generate recommendations for improvement"""
        recommendations = {
            "talent": [],
            "recruiter": []
        }

        # Talent recommendations
        if scores['skills_match'] < 15:
            recommendations["talent"].append("Consider highlighting more relevant skills from the job description")

        if scores['experience_fit'] < 10:
            recommendations["talent"].append("Add more details about your experience and achievements")

        if scores['education_match'] < 5:
            recommendations["talent"].append("Emphasize your education if it meets the requirements")

        # Recruiter recommendations
        if scores['overall_score'] < 60:
            recommendations["recruiter"].append("Candidate may not meet all requirements")
        elif scores['overall_score'] > 80:
            recommendations["recruiter"].append("Strong candidate worth considering")
        else:
            recommendations["recruiter"].append("Candidate meets basic requirements")

        return recommendations

    @staticmethod
    def _calculate_confidence(scores: Dict) -> int:
        """Calculate confidence in the scoring"""
        # Base confidence
        confidence = 70

        # Adjust based on data quality
        if scores.get('semantic_similarity', 0) > 30:
            confidence += 10
        if scores.get('skills_match', 0) > 15:
            confidence += 10
        if scores.get('penalties', 0) > 5:
            confidence -= 15

        return max(0, min(100, confidence))

    @staticmethod
    def _get_fallback_scores() -> Dict:
        """Return fallback scores when calculation fails"""
        return {
            "overall_score": 50,
            "component_scores": {
                "skills_match": 12,
                "experience_fit": 10,
                "education_match": 5,
                "semantic_similarity": 20,
                "penalties": 3
            },
            "evidence": {"matched_requirements": [], "missing_requirements": [], "concerns": []},
            "recommendations": {"talent": ["Unable to analyze"], "recruiter": ["Manual review"]},
            "confidence": 30
        }

    # Helper methods
    @staticmethod
    def _parse_years_from_job(job: Dict) -> float:
        """Parse years of experience from job entry"""
        dates = job.get('dates', '')
        if not dates:
            return 0

        try:
            # Simple parsing - would need more sophisticated logic
            if '-' in dates:
                start, end = dates.split('-')
                start_year = int(start.strip()[-4:]) if len(start.strip()) >= 4 else 0
                end_year = int(end.strip()[-4:]) if end.strip() != 'Present' else 2024
                return end_year - start_year
        except:
            pass

        return 0

    @staticmethod
    def _determine_seniority_level(title: str) -> str:
        """Determine seniority level from job title"""
        title_lower = title.lower()

        if any(word in title_lower for word in ['intern', 'trainee']):
            return 'intern'
        elif any(word in title_lower for word in ['junior', 'jr', 'associate', 'assistant']):
            return 'junior'
        elif any(word in title_lower for word in ['senior', 'sr', 'lead', 'principal']):
            return 'senior'
        elif any(word in title_lower for word in ['manager', 'director', 'vp', 'head']):
            return 'executive'
        else:
            return 'mid'