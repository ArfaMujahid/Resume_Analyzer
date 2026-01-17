import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from .models import ParsedResume


class ResumeStructurer:
    """Service for structuring and analyzing resume text"""

    # Common section headers
    SECTION_PATTERNS = {
        'summary': [
            r'(?i)(summary|profile|about|objective|overview)',
            r'(?i)(professional\s+summary|career\s+summary)'
        ],
        'experience': [
            r'(?i)(experience|work\s+experience|employment|professional\s+experience)',
            r'(?i)(work\s+history|career\s+history)'
        ],
        'education': [
            r'(?i)(education|academic|academic\s+background|qualifications)',
            r'(?i)(educational\s+background|training)'
        ],
        'skills': [
            r'(?i)(skills|technical\s+skills|core\s+competencies)',
            r'(?i)(competencies|expertise|proficiencies)'
        ],
        'certifications': [
            r'(?i)(certifications|certificates|credentials)',
            r'(?i)(professional\s+certifications|licenses)'
        ],
        'projects': [
            r'(?i)(projects|portfolio|personal\s+projects)',
            r'(?i)(key\s+projects|selected\s+projects)'
        ]
    }

    # Skills taxonomy (simplified)
    SKILLS_TAXONOMY = {
        'programming': [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
            'go', 'rust', 'swift', 'kotlin', 'scala', 'perl', 'r', 'matlab'
        ],
        'web_development': [
            'html', 'css', 'react', 'vue', 'angular', 'nodejs', 'express', 'django',
            'flask', 'rails', 'laravel', 'spring', 'asp.net', 'wordpress'
        ],
        'databases': [
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'oracle', 'sqlserver', 'cassandra', 'dynamodb', 'firebase'
        ],
        'cloud': [
            'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'terraform',
            'ansible', 'jenkins', 'ci/cd', 'devops', 'microservices', 'serverless'
        ],
        'tools': [
            'git', 'github', 'gitlab', 'jira', 'confluence', 'slack', 'trello',
            'figma', 'sketch', 'adobe', 'microsoft office', 'excel', 'powerpoint'
        ],
        'soft_skills': [
            'leadership', 'communication', 'teamwork', 'problem solving', 'analytical',
            'critical thinking', 'creativity', 'adaptability', 'time management',
            'project management', 'collaboration', 'presentation'
        ]
    }

    # Title seniority levels
    SENIORITY_LEVELS = {
        'intern': ['intern', 'internship', 'trainee'],
        'junior': ['junior', 'jr', 'entry level', 'associate', 'assistant'],
        'mid': ['mid', 'regular', 'professional', 'specialist'],
        'senior': ['senior', 'sr', 'lead', 'principal', 'head'],
        'executive': ['manager', 'director', 'vp', 'vice president', 'c-level', 'ceo', 'cto']
    }

    @staticmethod
    def detect_sections(text: str) -> Dict[str, Tuple[int, int]]:
        """Detect different sections in resume text"""
        sections = {}
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue

            # Check if this line matches any section pattern
            for section_name, patterns in ResumeStructurer.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, line_clean):
                        # Store section start position
                        if section_name not in sections:
                            sections[section_name] = (i, len(lines) - 1)
                        break

        return sections

    @staticmethod
    def extract_contact_info(text: str) -> Dict[str, str]:
        """Extract contact information from text"""
        contact_info = {}

        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]

        # Phone pattern (simplified)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"

        # LinkedIn pattern
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_matches = re.findall(linkedin_pattern, text)
        if linkedin_matches:
            contact_info['linkedin'] = f"https://{linkedin_matches[0]}"

        # GitHub pattern
        github_pattern = r'github\.com/[\w-]+'
        github_matches = re.findall(github_pattern, text)
        if github_matches:
            contact_info['github'] = f"https://{github_matches[0]}"

        return contact_info

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract skills from text using taxonomy"""
        found_skills = set()
        text_lower = text.lower()

        # Check each skill category
        for category, skills in ResumeStructurer.SKILLS_TAXONOMY.items():
            for skill in skills:
                # Use word boundaries to avoid partial matches
                pattern = rf'\b{re.escape(skill)}\b'
                if re.search(pattern, text_lower):
                    found_skills.add(skill.title())

        # Also extract skills from explicit skills section
        skills_section = ResumeStructurer._extract_section_text(text, 'skills')
        if skills_section:
            # Look for comma-separated skills
            comma_skills = [s.strip().title() for s in skills_section.split(',')]
            found_skills.update(comma_skills)

            # Look for bullet-point skills
            bullet_skills = re.findall(r'•\s*([^\n•]+)', skills_section)
            found_skills.update([s.strip().title() for s in bullet_skills])

        return sorted(list(found_skills))

    @staticmethod
    def extract_employment_history(text: str) -> List[Dict[str, Any]]:
        """Extract employment history from text"""
        employment = []
        experience_section = ResumeStructurer._extract_section_text(text, 'experience')

        if not experience_section:
            return employment

        # Pattern for job entries
        # This is a simplified pattern - real implementation would be more sophisticated
        job_pattern = r'''
            (?P<title>[^\n•]+?)\s*[\n•]\s*
            (?P<company>[^\n•]+?)\s*[\n•]\s*
            (?P<dates>[^\n•]+?)\s*[\n•]\s*
            (?P<description>.*?)(?=\n[A-Z][A-Z\s]*\n|\n•|\Z)
        '''

        matches = re.finditer(job_pattern, experience_section, re.VERBOSE | re.DOTALL)

        for match in matches:
            job_entry = {
                'title': match.group('title').strip(),
                'company': match.group('company').strip(),
                'dates': match.group('dates').strip(),
                'description': match.group('description').strip(),
                'bullets': ResumeStructurer._extract_bullets(match.group('description'))
            }

            # Try to parse dates
            start_date, end_date = ResumeStructurer._parse_dates(job_entry['dates'])
            job_entry['start_date'] = start_date
            job_entry['end_date'] = end_date

            employment.append(job_entry)

        return employment

    @staticmethod
    def extract_education(text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education = []
        education_section = ResumeStructurer._extract_section_text(text, 'education')

        if not education_section:
            return education

        # Pattern for education entries
        edu_pattern = r'''
            (?P<degree>[^\n•,]+?(?:Degree|Certificate|Diploma|Master|Bachelor|PhD)[^\n•,]*?)\s*[\n•,]\s*
            (?P<institution>[^\n•,]+?)\s*[\n•,]\s*
            (?P<dates>[^\n•,]*?)(?:\s*[\n•,]\s*|$)
            (?P<details>.*?)(?=\n[A-Z][A-Z\s]*\n|\n•|\Z)
        '''

        matches = re.finditer(edu_pattern, education_section, re.VERBOSE | re.DOTALL)

        for match in matches:
            edu_entry = {
                'degree': match.group('degree').strip(),
                'institution': match.group('institution').strip(),
                'dates': match.group('dates').strip(),
                'details': match.group('details').strip() if match.group('details') else ''
            }

            education.append(edu_entry)

        return education

    @staticmethod
    def extract_certifications(text: str) -> List[Dict[str, str]]:
        """Extract certifications"""
        certifications = []
        cert_section = ResumeStructurer._extract_section_text(text, 'certifications')

        if not cert_section:
            return certifications

        # Extract certification lines
        cert_lines = re.findall(r'•\s*([^\n•]+)', cert_section)
        for line in cert_lines:
            cert_info = {'name': line.strip()}
            certifications.append(cert_info)

        return certifications

    @staticmethod
    def normalize_titles(titles: List[str]) -> List[str]:
        """Normalize job titles"""
        normalized = []

        for title in titles:
            title_clean = title.strip().lower()

            # Map common variations
            title_mappings = {
                'sr': 'senior',
                'jr': 'junior',
                'sw': 'software',
                'swe': 'software engineer',
                'se': 'software engineer',
                'ds': 'data scientist',
                'de': 'data engineer',
                'pm': 'project manager',
                'po': 'product owner'
            }

            for short, full in title_mappings.items():
                title_clean = title_clean.replace(short, full)

            normalized.append(title_clean.title())

        return normalized

    @staticmethod
    def assess_quality(text: str, structured_data: Dict) -> Dict[str, Any]:
        """Assess the quality of parsed resume data"""
        quality_flags = {}
        score = 100

        # Check for missing sections
        required_sections = ['experience', 'education', 'skills']
        for section in required_sections:
            if section not in structured_data or not structured_data[section]:
                quality_flags[f'missing_{section}'] = True
                score -= 20

        # Check for dates
        if 'employment_history' in structured_data:
            has_dates = any(job.get('start_date') for job in structured_data['employment_history'])
            if not has_dates:
                quality_flags['missing_dates'] = True
                score -= 15

        # Check text length
        if len(text) < 500:
            quality_flags['too_short'] = True
            score -= 25
        elif len(text) > 10000:
            quality_flags['too_long'] = True
            score -= 10

        # Check for contact info
        contact_info = ResumeStructurer.extract_contact_info(text)
        if not contact_info.get('email'):
            quality_flags['missing_email'] = True
            score -= 10

        return {
            'score': max(0, score),
            'flags': quality_flags,
            'completeness': 100 - score
        }

    @staticmethod
    def structure_resume(parsed_resume: ParsedResume) -> bool:
        """Main method to structure resume data"""
        try:
            text = parsed_resume.raw_text
            if not text:
                return False

            # Extract all components
            structured_data = {
                'contact_info': ResumeStructurer.extract_contact_info(text),
                'sections': ResumeStructurer.detect_sections(text),
                'skills': ResumeStructurer.extract_skills(text),
                'employment_history': ResumeStructurer.extract_employment_history(text),
                'education': ResumeStructurer.extract_education(text),
                'certifications': ResumeStructurer.extract_certifications(text),
                'summary': ResumeStructurer._extract_section_text(text, 'summary'),
                'projects': ResumeStructurer._extract_section_text(text, 'projects')
            }

            # Extract titles from employment history
            titles = [job['title'] for job in structured_data.get('employment_history', [])]
            structured_data['titles_normalized'] = ResumeStructurer.normalize_titles(titles)

            # Extract companies
            companies = [job['company'] for job in structured_data.get('employment_history', [])]
            structured_data['companies'] = companies

            # Assess quality
            structured_data['quality_flags'] = ResumeStructurer.assess_quality(text, structured_data)

            # Update the parsed resume
            parsed_resume.structured_json = structured_data
            parsed_resume.skills_normalized = structured_data['skills']
            parsed_resume.titles_normalized = structured_data['titles_normalized']
            parsed_resume.companies = structured_data['companies']
            parsed_resume.employment_history = structured_data['employment_history']
            parsed_resume.education = structured_data['education']
            parsed_resume.certifications = structured_data['certifications']
            parsed_resume.quality_flags = structured_data['quality_flags']

            # Create section index
            section_index = {}
            for section_name, (start, end) in structured_data['sections'].items():
                section_index[section_name] = {
                    'start_line': start,
                    'end_line': end,
                    'character_count': len('\n'.join(text.split('\n')[start:end+1]))
                }
            parsed_resume.section_index = section_index

            parsed_resume.save()

            # Trigger next step (chunking)
            from .tasks import chunk_resume_task
            chunk_resume_task.delay(parsed_resume.id)

            return True

        except Exception as e:
            print(f"Resume structuring error: {str(e)}")
            return False

    # Helper methods
    @staticmethod
    def _extract_section_text(text: str, section_name: str) -> Optional[str]:
        """Extract text for a specific section"""
        sections = ResumeStructurer.detect_sections(text)
        if section_name not in sections:
            return None

        start, end = sections[section_name]
        lines = text.split('\n')
        return '\n'.join(lines[start:end+1])

    @staticmethod
    def _extract_bullets(text: str) -> List[str]:
        """Extract bullet points from text"""
        bullets = []

        # Extract bullet points with various markers
        bullet_patterns = [
            r'•\s*(.+)',
            r'-\s*(.+)',
            r'*\s*(.+)',
            r'\d+\.\s*(.+)'  # Numbered lists
        ]

        for pattern in bullet_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            bullets.extend(matches)

        return [bullet.strip() for bullet in bullets if bullet.strip()]

    @staticmethod
    def _parse_dates(date_string: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse date string into start and end dates"""
        if not date_string:
            return None, None

        # Common date patterns
        date_patterns = [
            (r'(\w+\s+\d{4})\s*-\s*(\w+\s+\d{4})', '%b %Y'),  # Jan 2020 - Dec 2021
            (r'(\d{4})\s*-\s*(\d{4})', '%Y'),  # 2020 - 2021
            (r'(\w+\s+\d{4})\s*-\s*(Present)', '%b %Y'),  # Jan 2020 - Present
            (r'(\w+\s+\d{4})', '%b %Y'),  # Jan 2020
        ]

        for pattern, date_format in date_patterns:
            match = re.search(pattern, date_string)
            if match:
                try:
                    start_str = match.group(1)
                    end_str = match.group(2) if len(match.groups()) > 1 else None

                    start_date = datetime.strptime(start_str, date_format).isoformat()
                    end_date = datetime.strptime(end_str, date_format).isoformat() if end_str else None

                    return start_date, end_date
                except ValueError:
                    continue

        return None, None