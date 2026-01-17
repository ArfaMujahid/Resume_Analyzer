import os
import json
import re
import requests
from typing import Dict, List, Any, Optional
from openai import OpenAI

from django.conf import settings
from decouple import config, Csv

class OpenRouterService:
    """Service for AI integration using OpenRouter API"""
    

    def __init__(self):
        self.api_key = config('OPENROUTER_API_KEY', default='')
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = "mistralai/devstral-2512:free"
        self.embedding_model = "openai/text-embedding-3-small"

        # Optional headers for OpenRouter rankings
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": config('SITE_URL', default='http://localhost:8000'),
            "X-Title": config('SITE_NAME', default='Resume Analyzer'),
            "Content-Type": "application/json"
        }

        # Initialize OpenAI client for OpenRouter
        # Only pass parameters that are supported
        client_kwargs = {
            "base_url": self.base_url,
            "api_key": self.api_key
        }

        # Add headers only if they're not empty
        if self.headers.get("HTTP-Referer") and self.headers.get("X-Title"):
            client_kwargs["default_headers"] = {
                "HTTP-Referer": self.headers["HTTP-Referer"],
                "X-Title": self.headers["X-Title"]
            }

        # Commented out due to proxy error - using requests instead
        # self.client = OpenAI(**client_kwargs)

    async def analyze_resume_match(self, resume_text: str, job_description: str,
                                   resume_structured: Dict = None) -> Dict[str, Any]:
        """
        Analyze resume against job description using OpenRouter

        Args:
            resume_text: Raw resume text
            job_description: Job description text
            resume_structured: Structured resume data (optional)

        Returns:
            Analysis results with scores and evidence
        """
        try:
            jd_lower = job_description.strip().lower()
            jd_words = jd_lower.split()
            invalid_indicators = [
                len(job_description.strip()) < 100,  # Too short
                job_description.strip() == jd_lower,  # All lowercase
                len(set(jd_words)) < 10,  # Too few unique words
                any(word in jd_lower for word in [
                    'dsadasd', 'asdfgh', 'qwerty',
                    'sample text', 'placeholder text'
                ]),
                # Check if it's mostly random characters
                sum(1 for c in job_description if c.isalnum()) / len(job_description) < 0.7
                if job_description else False
            ]

            if any(invalid_indicators):
                raise ValueError(
                    "Invalid job description. Please provide a real job "
                    "description with specific requirements and qualifications."
                )

            # Prepare context within token limits
            context = self._prepare_analysis_context(
                resume_text, job_description, resume_structured
            )

            # Create the analysis prompt
            prompt = self._create_analysis_prompt(context)

            # Prepare request data according to OpenRouter API
            data = {
                "model": self.default_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert resume analyst. Provide detailed analysis in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for consistency
                "max_tokens": 8192  # Maximum allowed to ensure complete responses
            }

            # Make direct API call to OpenRouter
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=60  # Increased timeout for longer responses
            )

            response.raise_for_status()

            # Parse and validate response
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"AI Response length: {len(content)} characters")
                print(f"AI Response preview: {content[:500]}...")

                # Clean up the content - remove markdown code blocks if present
                if '```' in content:
                    # Remove everything between ``` markers
                    content = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', content)
                    # Also handle case where closing ``` is missing
                    content = re.sub(r'```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)

                try:
                    # Check if content might be truncated
                    if not content.strip().endswith('}') and not content.strip().endswith(']'):
                        print("Warning: Response appears to be truncated")
                        print(f"Content ends with: {repr(content[-50:])}")
                        # Try to fix common truncation issues
                        if content.count('{') > content.count('}'):
                            missing_brackets = content.count('{') - content.count('}')
                            content += '}' * missing_brackets
                            print(f"Added {missing_brackets} closing brackets")
                        if content.count('[') > content.count(']'):
                            missing_brackets = content.count('[') - content.count(']')
                            content += ']' * missing_brackets
                            print(f"Added {missing_brackets} closing square brackets")

                    parsed_result = json.loads(content)
                    print(f"Successfully parsed JSON with {len(parsed_result)} top-level keys")
                    return self._validate_analysis_result(parsed_result)
                except json.JSONDecodeError as je:
                    print(f"JSON decode error: {str(je)}")
                    print(f"Content length: {len(content)}")
                    print(f"Content that failed to parse (first 1000 chars): {content[:1000]}")
                    # Check if it's a truncation issue
                    if "Unterminated string" in str(je) or "Expecting ',' delimiter" in str(je):
                        raise Exception("API response was truncated. Please try again.")
                    raise Exception(f"Failed to parse API response: {str(je)}")
            else:
                print("Invalid response format from OpenRouter")
                print(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                raise Exception("Invalid response format from API")

        except Exception as e:
            print(f"OpenRouter API error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            raise e

    def _prepare_analysis_context(self, resume_text: str, job_description: str,
                                  resume_structured: Dict = None) -> Dict[str, Any]:
        """Prepare context within token limits"""
        # Validate inputs
        if not job_description or len(job_description.strip()) < 50:
            raise ValueError("Job description is too short or empty. Please provide a detailed job description.")

        if not resume_text or len(resume_text.strip()) < 50:
            raise ValueError("Resume text is too short or empty. Please provide a detailed resume.")

        # Check for invalid job description content
        jd_lower = job_description.lower()
        jd_words = jd_lower.split()

        # Check for obviously invalid content
        invalid_indicators = [
            len(job_description.strip()) < 100,  # Too short
            job_description.strip() == jd_lower,  # All lowercase
            len(set(jd_words)) < 10,  # Too few unique words
            any(word in jd_lower for word in ['dsadasd', 'asdfgh', 'qwerty', 'sample text', 'placeholder text']),
            # Check if it's mostly random characters
            sum(1 for c in job_description if c.isalnum()) / len(job_description) < 0.7 if job_description else False
        ]

        if any(invalid_indicators):
            raise ValueError("Invalid job description. Please provide a real job description with specific requirements and qualifications.")

        # Truncate text if too long (OpenRouter free models have limits)
        max_chars = 12000  # Increased to preserve more content

        resume_summary = resume_text[:max_chars] if len(resume_text) > max_chars else resume_text
        jd_summary = job_description[:max_chars] if len(job_description) > max_chars else job_description

        context = {
            "resume_text": resume_summary,
            "job_description": jd_summary,
            "resume_structured": resume_structured or {}
        }

        return context

    def _create_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Create analysis prompt for OpenRouter"""
        prompt = f"""
        Analyze the match between this resume and job description. Return JSON with:

        {{
            "overall_score": 0-100,
            "component_scores": {{
                "skills_match": 0-25,
                "experience_fit": 0-20,
                "education_match": 0-10,
                "semantic_similarity": 0-40,
                "penalties": 0-10
            }},
            "matched_requirements": [
                {{
                    "jd_text": "requirement text",
                    "resume_snippets": ["evidence 1", "evidence 2"],
                    "similarity_score": 0.0-1.0
                }}
            ],
            "missing_requirements": ["missing skill 1", "missing skill 2"],
            "concerns": ["concern 1", "concern 2"],
            "recommendations": {{
                "talent": ["improvement 1", "improvement 2"],
                "recruiter": ["note 1", "note 2"]
            }},
            "confidence": 0-100
        }}

        JOB DESCRIPTION:
        {context['job_description']}

        RESUME:
        {context['resume_text']}

        IMPORTANT: Return ONLY the JSON object, no other text.
        """

        return prompt

    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and ensure required fields in analysis result"""
        print(f"Validating analysis result with keys: {list(result.keys())}")

        # Set defaults for missing fields
        defaults = {
            "overall_score": 50,
            "component_scores": {
                "skills_match": 0,
                "experience_fit": 0,
                "education_match": 0,
                "semantic_similarity": 0,
                "penalties": 0
            },
            "matched_requirements": [],
            "missing_requirements": [],
            "concerns": [],
            "recommendations": {
                "talent": [],
                "recruiter": []
            },
            "confidence": 50
        }

        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in result:
                print(f"Missing key '{key}', setting default")
                result[key] = default_value
            elif isinstance(default_value, dict) and isinstance(result[key], dict):
                for sub_key, sub_default in default_value.items():
                    if sub_key not in result[key]:
                        print(f"Missing sub-key '{sub_key}' in '{key}', setting default")
                        result[key][sub_key] = sub_default

        # Log the sizes of important arrays
        if 'matched_requirements' in result:
            print(f"Matched requirements count: {len(result['matched_requirements'])}")
        if 'missing_requirements' in result:
            print(f"Missing requirements count: {len(result['missing_requirements'])}")
        if 'concerns' in result:
            print(f"Concerns count: {len(result['concerns'])}")

        return result

    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks using OpenRouter

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []

            for text in texts:
                # Prepare request for embeddings
                data = {
                    "model": self.embedding_model,
                    "input": text
                }

                # Make API call to OpenRouter
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=data
                )

                response.raise_for_status()
                result = response.json()

                if 'data' in result and len(result['data']) > 0:
                    embeddings.append(result['data'][0]['embedding'])
                else:
                    print("Invalid embedding response format")
                    embeddings.append([0.0] * 1536)

            return embeddings

        except Exception as e:
            print(f"Embedding generation error: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * 1536 for _ in texts]

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0-1
        """
        try:
            # Generate embeddings
            embeddings = await self.generate_embeddings([text1, text2])

            if len(embeddings) < 2:
                return 0.0

            # Calculate cosine similarity
            import numpy as np

            vec1, vec2 = np.array(embeddings[0]), np.array(embeddings[1])

            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            print(f"Similarity calculation error: {str(e)}")
            return 0.0

    async def extract_skills_from_text(self, text: str, known_skills: List[str] = None) -> List[str]:
        """
        Extract skills from text using AI

        Args:
            text: Text to extract skills from
            known_skills: List of known skills to look for (optional)

        Returns:
            List of extracted skills
        """
        try:
            prompt = f"""
            Extract skills from the following resume text. Return JSON with:
            {{
                "skills": ["skill1", "skill2", "skill3"]
            }}

            TEXT:
            {text}

            Known skills to focus on: {known_skills if known_skills else []}
            Focus on technical skills, soft skills, and domain expertise.
            """

            # Prepare request data
            data = {
                "model": self.default_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a skill extraction expert. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }

            # Make API call to OpenRouter
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']

                # Clean up the content - remove markdown code blocks if present
                if '```' in content:
                    # Remove everything between ``` markers
                    content = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', content)
                    # Also handle case where closing ``` is missing
                    content = re.sub(r'```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)

                try:
                    parsed_result = json.loads(content)
                    return parsed_result.get("skills", [])
                except json.JSONDecodeError as je:
                    print(f"JSON decode error in skill extraction: {str(je)}")
                    print(f"Content that failed to parse: {content}")
                    return []
            else:
                print("Invalid response format from OpenRouter")
                return []

        except Exception as e:
            print(f"Skill extraction error: {str(e)}")
            return []

    def _structure_job_description(self, text: str) -> Dict[str, Any]:
        """
        Structure job description text into components

        Args:
            text: Job description text

        Returns:
            Structured job description data
        """
        try:
            prompt = f"""
            Structure this job description. Return JSON with:
            {{
                "requirements_required": ["req1", "req2"],
                "requirements_preferred": ["pref1", "pref2"],
                "responsibilities": ["resp1", "resp2"],
                "skills_required": ["skill1", "skill2"],
                "skills_preferred": ["skill3", "skill4"]
            }}

            TEXT:
            {text}

            Extract requirements, responsibilities, and skills.
            Separate required vs preferred where possible.
            """

            # Prepare request data
            data = {
                "model": self.default_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a job description analyst. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
            }

            # Make API call to OpenRouter
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                parsed_result = json.loads(content)
                return parsed_result
            else:
                print("Invalid response format from OpenRouter")
                return {
                    "requirements_required": [],
                    "requirements_preferred": [],
                    "responsibilities": [],
                    "skills_required": [],
                    "skills_preferred": []
                }

        except Exception as e:
            print(f"Job description structuring error: {str(e)}")
            return {
                "requirements_required": [],
                "requirements_preferred": [],
                "responsibilities": [],
                "skills_required": [],
                "skills_preferred": []
            }

    async def improve_resume_bullets(self, bullets: List[str], job_requirements: List[str]) -> List[str]:
        """
        Improve resume bullets to better match job requirements

        Args:
            bullets: List of resume bullet points
            job_requirements: List of job requirements

        Returns:
            List of improved bullet points
        """
        try:
            prompt = f"""
            Improve these resume bullets to better match the job requirements.
            Keep them truthful and professional. Return JSON with:
            {{
                "improved_bullets": ["improved bullet 1", "improved bullet 2"]
            }}

            ORIGINAL BULLETS:
            {json.dumps(bullets, indent=2)}

            JOB REQUIREMENTS:
            {json.dumps(job_requirements, indent=2)}

            Guidelines:
            - Use action verbs
            - Quantify achievements when possible
            - Include relevant keywords
            - Keep bullets concise and impactful
            - Do not invent experience
            """

            # Prepare request data
            data = {
                "model": self.default_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional resume writer. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 800
            }

            # Make API call to OpenRouter
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                parsed_result = json.loads(content)
                return parsed_result.get("improved_bullets", bullets)
            else:
                print("Invalid response format from OpenRouter")
                return bullets

        except Exception as e:
            print(f"Bullet improvement error: {str(e)}")
            return bullets


# Singleton instance
openrouter_service = OpenRouterService()
