
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import json
from openai import OpenAI
import numpy as np
import PyPDF2
from docx import Document
from langchain_openai import ChatOpenAI
import requests

import os
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import httpx

from .models import Candidate

# ============================================================================
# OPENAI API CONFIGURATION
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-y6zJFherQCsRN8jI8yQwQw"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or "https://genailab.tcs.in/v1"
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL") or "genailab-maas-gpt-4o"
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL") or "genailab-maas-gpt-4o"

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

if not OPENAI_API_KEY:
    print("⚠️  WARNING: No API key provided. Set OPENAI_API_KEY environment variable.")

print(f"🔗 Using OpenAI API base: {OPENAI_BASE_URL}")
print(f"📊 Embedding model: {OPENAI_EMBEDDING_MODEL}")
print(f"💬 Chat model: {OPENAI_CHAT_MODEL}")

# Create OpenAI client with custom httpx client (SSL verification disabled)
try:
    http_client = httpx.Client(verify=False, timeout=60.0)
    openai_client = OpenAI(
        api_key=OPENAI_API_KEY, 
        base_url=OPENAI_BASE_URL,
        http_client=http_client
    )
    print("✅ OpenAI client initialized successfully")
except Exception as e:
    print(f"❌ ERROR initializing OpenAI client: {type(e).__name__}: {e}")
    openai_client = None

# Legacy aliases for backward compatibility
api_key = OPENAI_API_KEY
api_base = OPENAI_BASE_URL
EMBEDDING_MODEL = OPENAI_EMBEDDING_MODEL
CHAT_MODEL = OPENAI_CHAT_MODEL



# ============================================================================
# AI ASSISTANCE CHATBOT ENDPOINT (MAIN CHATBOT INTERFACE)
# ============================================================================
@csrf_exempt
def ai_assist(request):
    """
    Main AI Assistance Chatbot Endpoint
    Handles chat requests from the hiring portal popup interface.
    Uses OpenAI client for reliable chat completions.
    """
    if request.method != 'POST':
        return JsonResponse({'answer': 'Invalid request method'}, status=405)
    
    try:
        # Parse incoming request
        data = json.loads(request.body.decode('utf-8'))
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({
                'success': False,
                'answer': 'Please provide a question or message.'
            })
        
        print(f"\n🤖 CHATBOT: Received question: {question[:50]}...")
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return JsonResponse({
                'success': False,
                'answer': 'Chat service is currently unavailable. Please try again later.'
            })
        
        
        # Call OpenAI API with proper chat completion
        print(f"📡 Calling OpenAI API (model: {OPENAI_CHAT_MODEL})...")
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HR assistant for the Green Skill Talent hiring platform. "
                              "Provide helpful, concise responses related to recruiting, candidate screening, "
                              "skill matching, and talent acquisition. Be professional and supportive."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract answer from response
        answer = response.choices[0].message.content.strip()
        print(f"✅ Chatbot response: {answer[:50]}...")
        
        return JsonResponse({
            'success': True,
            'answer': answer
        })
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Chatbot error: {type(e).__name__}: {error_msg}")
        return JsonResponse({
            'success': False,
            'answer': f'Error processing your request: {error_msg}'
        })






# ============================================================================
# PAGE VIEWS
# ============================================================================

def home(request):
    """Render home/login page"""
    return render(request, 'home.html')

def hiring_portal(request):
    """Render hiring portal with job listings and AI assistance"""
    return render(request, 'hiring_portal.html')

def match_engine(request):
    """Render match engine for candidate-to-job matching"""
    return render(request, 'match_engine.html')

def candidate_portal(request):
    """Render candidate portal with data from database and skill graphs"""
    try:
        # Load candidates from database
        candidates = Candidate.objects.all()
        
        # If database is empty, load from JSON file
        if not candidates.exists():
            load_candidates_from_json()
            candidates = Candidate.objects.all()
        
        # Serialize candidates to ensure skill_vectors is JSON
        candidates_list = []
        for candidate in candidates:
            candidate_dict = {
                'candidate_name': candidate.candidate_name,
                'skills': candidate.skills,
                'current_role': candidate.current_role,
                'proficiency_level': candidate.proficiency_level,
                'grade': candidate.grade or 'N/A',
                'employment_type': candidate.employment_type or 'N/A',
                'email': candidate.email or 'N/A',
                'phone': candidate.phone or 'N/A',
                'skill_vectors': candidate.skill_vectors if candidate.skill_vectors else [],
            }
            candidates_list.append(candidate_dict)
        
        # Aggregate data for graphs
        skill_counts = {}
        proficiency_counts = {}
        
        for candidate in candidates:
            # Count skills
            if candidate.skills:
                skill_counts[candidate.skills] = skill_counts.get(candidate.skills, 0) + 1
            
            # Count proficiency levels
            if candidate.proficiency_level:
                prof = candidate.proficiency_level
                proficiency_counts[prof] = proficiency_counts.get(prof, 0) + 1
        
        # Prepare data for Chart.js (skills distribution)
        skills_labels = list(skill_counts.keys())
        skills_data = list(skill_counts.values())
        
        # Prepare data for Chart.js (proficiency distribution)
        proficiency_labels = list(proficiency_counts.keys())
        proficiency_data = list(proficiency_counts.values())
        
        # Serialize candidates with skill_vectors as JSON strings
        for candidate_dict in candidates_list:
            candidate_dict['skill_vectors_json'] = json.dumps(candidate_dict['skill_vectors'])
        
        context = {
            'candidates': candidates_list,
            'skills_labels': json.dumps(skills_labels),
            'skills_data': json.dumps(skills_data),
            'proficiency_labels': json.dumps(proficiency_labels),
            'proficiency_data': json.dumps(proficiency_data),
            'total_candidates': len(candidates_list),
        }
        
        return render(request, 'candidate_portal.html', context)
    except Exception as e:
        print(f"Error loading candidate portal: {e}")
        import traceback
        traceback.print_exc()
        return render(request, 'candidate_portal.html', {'error': str(e)})


def load_candidates_from_json():
    """Load candidates from Candiates_profiles.json into database"""
    try:
        loaded_count = 0
        
        # Load from Candiates_profiles.json
        json_path = r"c:\Users\GENAIMXCDMXUSR16\Pictures\Candiates_profiles.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            # The file is a direct array of candidates
            candidates_data = json.load(f)
        
        # Handle both cases: direct array or object with 'candidates' key
        if isinstance(candidates_data, list):
            candidates_list = candidates_data
        else:
            candidates_list = candidates_data.get('candidates', [])
        
        for item in candidates_list:
            candidate_name = item.get('name', '')
            if not candidate_name:
                continue
            
            email = item.get('email', '')
            current_role = item.get('current_role', '')
            grade = item.get('grade', '')
            employment_type = item.get('employment_type', '')
            phone = item.get('phone', '')
            skill_vectors = item.get('skill_vectors', [])
            
            # Get primary skill from skill_vectors
            primary_skill = skill_vectors[0].get('skill', '') if skill_vectors else ''
            primary_proficiency = skill_vectors[0].get('proficiency_level', 'Intermediate') if skill_vectors else 'Intermediate'
            
            # Create candidate in database
            candidate = Candidate.objects.create(
                candidate_name=candidate_name,
                skills=primary_skill,
                current_role=current_role,
                grade=grade,
                employment_type=employment_type,
                phone=phone,
                proficiency_level=primary_proficiency,
                email=email,
                skill_vectors=skill_vectors,
            )
            loaded_count += 1
        
        print(f"✅ Loaded {loaded_count} candidates from Candiates_profiles.json")
    except Exception as e:
        print(f"❌ Error loading candidates from JSON: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# RANKED CANDIDATE SHORTLIST & LEARNING PLAN FEATURES
# ============================================================================

def get_role_candidates_ranked(request, role=None):
    """
    Get ranked candidates for a specific role with match scores and rationale
    """
    try:
        # Define common roles and their required skills
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'key_skills': ['Cloud Cost Optimization', 'Performance Monitoring'],
                'proficiency_level': 'Intermediate'
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization', 'Infrastructure Monitoring'],
                'key_skills': ['CI/CD Pipelines', 'Docker', 'Container Optimization'],
                'proficiency_level': 'Intermediate'
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python', 'Performance Optimization'],
                'key_skills': ['Algorithm Optimization', 'Energy Efficient Coding'],
                'proficiency_level': 'Intermediate'
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python', 'Tableau', 'Power BI'],
                'key_skills': ['Data Analytics', 'ESG Reporting', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance', 'Infrastructure Monitoring'],
                'key_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure'],
                'proficiency_level': 'Intermediate'
            }
        }

        if not role:
            role = request.GET.get('role', 'Cloud Efficiency Engineer')

        role_req = ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS['Cloud Efficiency Engineer'])
        candidates = Candidate.objects.all()

        ranked_candidates = []

        for candidate in candidates:
            # Get candidate skills from skill_vectors
            candidate_skills = []
            if candidate.skill_vectors:
                candidate_skills = [s.get('skill', '').lower() for s in candidate.skill_vectors]

            # Calculate matched skills
            matched_skills = []
            missing_skills = []

            for req_skill in role_req['required_skills']:
                found = False
                for cand_skill in candidate_skills:
                    if req_skill.lower() in cand_skill or cand_skill in req_skill.lower():
                        matched_skills.append(req_skill)
                        found = True
                        break
                if not found:
                    missing_skills.append(req_skill)

            # Calculate match score (0-100)
            if len(role_req['required_skills']) > 0:
                match_score = (len(matched_skills) / len(role_req['required_skills'])) * 100
            else:
                match_score = 0

            # Get proficiency level bonus
            prof_bonus = 0
            if candidate.proficiency_level and candidate.proficiency_level.lower() == 'expert':
                prof_bonus = 10
            elif candidate.proficiency_level and candidate.proficiency_level.lower() == 'advanced':
                prof_bonus = 5

            final_score = min(100, match_score + prof_bonus)

            ranked_candidates.append({
                'candidate_name': candidate.candidate_name,
                'email': candidate.email,
                'phone': candidate.phone,
                'current_role': candidate.current_role,
                'grade': candidate.grade,
                'employment_type': candidate.employment_type,
                'match_score': round(final_score, 1),
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'proficiency_level': candidate.proficiency_level,
                'skill_vectors': candidate.skill_vectors or []
            })

        # Sort by match score descending
        ranked_candidates.sort(key=lambda x: x['match_score'], reverse=True)

        # Get available roles
        available_roles = list(ROLE_REQUIREMENTS.keys())

        context = {
            'ranked_candidates': ranked_candidates,
            'selected_role': role,
            'available_roles': available_roles,
            'top_candidates': ranked_candidates[:10]  # Top 10 candidates
        }

        return render(request, 'candidate_shortlist.html', context)

    except Exception as e:
        print(f"Error in get_role_candidates_ranked: {e}")
        import traceback
        traceback.print_exc()
        return render(request, 'candidate_shortlist.html', {'error': str(e)})


@csrf_exempt
def get_candidate_learning_plan(request):
    """
    Generate learning plan for a candidate based on role requirements
    """
    try:
        role = request.GET.get('role', 'Cloud Efficiency Engineer')
        candidate_name = request.GET.get('candidate_name', '')

        if not candidate_name:
            return JsonResponse({'success': False, 'error': 'Candidate name required'})

        # Get candidate from DB
        try:
            candidate = Candidate.objects.get(candidate_name=candidate_name)
        except Candidate.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Candidate not found'})

        # Role requirements
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'proficiency_levels': {'Cloud Cost Optimization': 'Expert', 'Performance Monitoring': 'Intermediate', 'FinOps': 'Intermediate'}
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization'],
                'proficiency_levels': {'CI/CD Pipelines': 'Expert', 'Docker': 'Expert', 'Container Optimization': 'Intermediate'}
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python'],
                'proficiency_levels': {'Algorithm Optimization': 'Expert', 'Energy Efficient Coding': 'Intermediate', 'Python': 'Expert'}
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python'],
                'proficiency_levels': {'Data Analytics': 'Expert', 'ESG Reporting': 'Intermediate', 'SQL': 'Intermediate'}
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance'],
                'proficiency_levels': {'Sustainable IT Practices': 'Expert', 'Energy Efficient Infrastructure': 'Intermediate', 'IT Governance': 'Basic'}
            }
        }

        role_req = ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS['Cloud Efficiency Engineer'])

        # Get candidate current skills
        current_skills = {}
        if candidate.skill_vectors:
            for skill in candidate.skill_vectors:
                current_skills[skill.get('skill', '')] = {
                    'proficiency': skill.get('proficiency_level', 'Basic'),
                    'score': skill.get('skill_level_score', 0)
                }

        # Build learning plan
        learning_plan = []
        gap_count = 0

        for req_skill in role_req['required_skills']:
            required_prof = role_req['proficiency_levels'].get(req_skill, 'Intermediate')

            if req_skill in current_skills:
                current_prof = current_skills[req_skill]['proficiency']
                current_score = current_skills[req_skill]['score']

                # Check if proficiency needs improvement
                prof_levels = {'Basic': 1, 'Intermediate': 2, 'Advanced': 3, 'Expert': 4}
                req_level = prof_levels.get(required_prof, 2)
                curr_level = prof_levels.get(current_prof, 1)

                if curr_level < req_level:
                    gap_count += 1
                    learning_plan.append({
                        'skill': req_skill,
                        'status': 'improvement_needed',
                        'current_level': current_prof,
                        'required_level': required_prof,
                        'current_score': current_score,
                        'gap': req_level - curr_level,
                        'duration': f'{(req_level - curr_level) * 2}-{(req_level - curr_level) * 4} weeks'
                    })
                else:
                    learning_plan.append({
                        'skill': req_skill,
                        'status': 'proficient',
                        'current_level': current_prof,
                        'required_level': required_prof,
                        'current_score': current_score,
                        'gap': 0,
                        'duration': 'Ready'
                    })
            else:
                gap_count += 1
                learning_plan.append({
                    'skill': req_skill,
                    'status': 'new_skill',
                    'current_level': 'None',
                    'required_level': required_prof,
                    'current_score': 0,
                    'gap': 3,
                    'duration': '8-12 weeks'
                })

        # Calculate readiness percentage
        readiness = ((len(learning_plan) - gap_count) / len(learning_plan)) * 100 if learning_plan else 0

        result = {
            'success': True,
            'candidate_name': candidate.candidate_name,
            'role': role,
            'current_role': candidate.current_role,
            'email': candidate.email,
            'readiness_percentage': round(readiness, 1),
            'learning_plan': learning_plan,
            'gap_count': gap_count,
            'total_skills': len(learning_plan)
        }

        return JsonResponse(result)

    except Exception as e:
        print(f"Error in get_candidate_learning_plan: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


def get_role_candidates_popup(request):
    """
    Get candidates for a specific role to display in popup modal
    """
    try:
        role = request.GET.get('role', '')
        if not role:
            return JsonResponse({'success': False, 'error': 'No role specified'})

        # Define common roles and their required skills
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'key_skills': ['Cloud Cost Optimization', 'Performance Monitoring'],
                'proficiency_level': 'Intermediate'
            },
            'Green Cloud Architect': {
                'required_skills': ['Cloud Architecture', 'Cloud Security', 'Cost Optimization', 'AWS', 'Azure', 'GCP'],
                'key_skills': ['Cloud Architecture', 'Cloud Security', 'Cost Optimization'],
                'proficiency_level': 'Advanced'
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization', 'Infrastructure Monitoring'],
                'key_skills': ['CI/CD Pipelines', 'Docker', 'Container Optimization'],
                'proficiency_level': 'Intermediate'
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python', 'Performance Optimization'],
                'key_skills': ['Algorithm Optimization', 'Energy Efficient Coding'],
                'proficiency_level': 'Intermediate'
            },
            'Data Scientist': {
                'required_skills': ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics', 'Pandas', 'NumPy'],
                'key_skills': ['Python', 'Machine Learning', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python', 'Tableau', 'Power BI'],
                'key_skills': ['Data Analytics', 'ESG Reporting', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'DevOps Engineer': {
                'required_skills': ['CI/CD', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'Linux', 'AWS'],
                'key_skills': ['CI/CD', 'Docker', 'Kubernetes'],
                'proficiency_level': 'Intermediate'
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance', 'Infrastructure Monitoring'],
                'key_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure'],
                'proficiency_level': 'Intermediate'
            }
        }

        role_req = ROLE_REQUIREMENTS.get(role)
        if not role_req:
            return JsonResponse({'success': False, 'error': f'Role "{role}" not found'})

        candidates = Candidate.objects.all()
        matching_candidates = []

        for candidate in candidates:
            # Get candidate skills from skill_vectors
            candidate_skills = []
            if candidate.skill_vectors:
                candidate_skills = [s.get('skill', '').lower() for s in candidate.skill_vectors]

            # Calculate matched skills
            matched_skills = []
            for req_skill in role_req['required_skills']:
                for cand_skill in candidate_skills:
                    if req_skill.lower() in cand_skill or cand_skill in req_skill.lower():
                        matched_skills.append(req_skill)
                        break

            # Only include candidates with at least one matching skill
            if matched_skills:
                # Calculate match score
                match_score = (len(matched_skills) / len(role_req['required_skills'])) * 100

                matching_candidates.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'current_role': candidate.current_role or 'N/A',
                    'proficiency_level': candidate.proficiency_level or 'Intermediate',
                    'email': candidate.email or 'N/A',
                    'phone': candidate.phone or 'N/A',
                    'matched_skills': matched_skills,
                    'match_score': round(match_score, 1),
                    'total_required_skills': len(role_req['required_skills'])
                })

        # Sort by match score (highest first)
        matching_candidates.sort(key=lambda x: x['match_score'], reverse=True)

        return JsonResponse({
            'success': True,
            'role': role,
            'required_skills': role_req['required_skills'],
            'candidates': matching_candidates,
            'total_candidates': len(matching_candidates)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def export_candidates_csv(request):
    """
    Export ranked candidates for a specific role to CSV format
    """
    try:
        import csv
        from django.http import HttpResponse

        role = request.GET.get('role', 'Cloud Efficiency Engineer')

        # Define common roles and their required skills
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'key_skills': ['Cloud Cost Optimization', 'Performance Monitoring'],
                'proficiency_level': 'Intermediate'
            },
            'Green Cloud Architect': {
                'required_skills': ['Cloud Architecture', 'Cloud Security', 'Cost Optimization', 'AWS', 'Azure', 'GCP'],
                'key_skills': ['Cloud Architecture', 'Cloud Security', 'Cost Optimization'],
                'proficiency_level': 'Advanced'
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization', 'Infrastructure Monitoring'],
                'key_skills': ['CI/CD Pipelines', 'Docker', 'Container Optimization'],
                'proficiency_level': 'Intermediate'
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python', 'Performance Optimization'],
                'key_skills': ['Algorithm Optimization', 'Energy Efficient Coding'],
                'proficiency_level': 'Intermediate'
            },
            'Data Scientist': {
                'required_skills': ['Python', 'Machine Learning', 'SQL', 'Data Analysis', 'Statistics', 'Pandas', 'NumPy'],
                'key_skills': ['Python', 'Machine Learning', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python', 'Tableau', 'Power BI'],
                'key_skills': ['Data Analytics', 'ESG Reporting', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'DevOps Engineer': {
                'required_skills': ['CI/CD', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'Linux', 'AWS'],
                'key_skills': ['CI/CD', 'Docker', 'Kubernetes'],
                'proficiency_level': 'Intermediate'
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance', 'Infrastructure Monitoring'],
                'key_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure'],
                'proficiency_level': 'Intermediate'
            }
        }

        role_req = ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS['Cloud Efficiency Engineer'])
        candidates = Candidate.objects.all()

        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="candidates_{role.replace(" ", "_")}.csv"'

        writer = csv.writer(response)
        # Write header row
        writer.writerow([
            'Rank', 'Candidate Name', 'Current Role', 'Proficiency Level',
            'Match Score (%)', 'Matched Skills', 'Missing Skills',
            'Email', 'Phone', 'Grade', 'Employment Type'
        ])

        rank = 1
        for candidate in candidates:
            # Get candidate skills from skill_vectors
            candidate_skills = []
            if candidate.skill_vectors:
                candidate_skills = [s.get('skill', '').lower() for s in candidate.skill_vectors]

            # Calculate matched skills
            matched_skills = []
            missing_skills = []

            for req_skill in role_req['required_skills']:
                found = False
                for cand_skill in candidate_skills:
                    if req_skill.lower() in cand_skill or cand_skill in req_skill.lower():
                        matched_skills.append(req_skill)
                        found = True
                        break
                if not found:
                    missing_skills.append(req_skill)

            # Calculate match score (0-100)
            if len(role_req['required_skills']) > 0:
                match_score = (len(matched_skills) / len(role_req['required_skills'])) * 100
            else:
                match_score = 0

            # Only include candidates with some matching skills
            if matched_skills:
                writer.writerow([
                    rank,
                    candidate.candidate_name,
                    candidate.current_role or 'N/A',
                    candidate.proficiency_level or 'Intermediate',
                    f"{match_score:.1f}",
                    '; '.join(matched_skills),
                    '; '.join(missing_skills),
                    candidate.email or 'N/A',
                    candidate.phone or 'N/A',
                    candidate.grade or 'N/A',
                    candidate.employment_type or 'N/A'
                ])
                rank += 1

        return response

    except Exception as e:
        # Return error as CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="error.csv"'
        writer = csv.writer(response)
        writer.writerow(['Error', str(e)])
        return response


# ============================================================================
# CANDIDATE-JOB MATCHING & ANALYSIS FUNCTIONS
# ============================================================================

@csrf_exempt
def analyze_bulk_matching(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Get the skills input
        required_skills = request.POST.get('skills', '').strip()
        if not required_skills:
            return JsonResponse({'success': False, 'error': 'No skills provided'})
        
        # Parse required skills (handle both comma and newline separated)
        required_skills_list = [skill.strip() for skill in required_skills.replace('\n', ',').split(',') if skill.strip()]
        
        # Get the uploaded file
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        # Parse the file based on extension
        file_name = excel_file.name.lower()
        results = []
        
        try:
            if file_name.endswith('.csv'):
                results = parse_csv_file(excel_file, required_skills_list)
            elif file_name.endswith(('.xlsx', '.xls')):
                results = parse_excel_file(excel_file, required_skills_list)
            else:
                return JsonResponse({'success': False, 'error': 'Invalid file format. Please upload Excel (.xlsx, .xls) or CSV file.'})
        except Exception as file_error:
            return JsonResponse({'success': False, 'error': f'File processing error: {str(file_error)}'})
        
        if not results:
            return JsonResponse({'success': False, 'error': 'No valid candidate data found in the file. Please check the format.'})
        
        return JsonResponse({'success': True, 'results': results})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'})

def parse_excel_file(excel_file, required_skills_list):
    """
    Parse Excel file (.xlsx, .xls) and analyze candidate skills using OpenAI embeddings
    """
    results = []
    try:
        # Read Excel file using pandas
        df = pd.read_excel(excel_file)
        
        # Get embeddings for required skills as plain text
        required_skills_str = ", ".join(required_skills_list)
        required_embedding = get_embedding(required_skills_str)
        
        # Process each row
        for idx, row in df.iterrows():
            # Get first column as candidate name
            candidate_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            
            if not candidate_name or candidate_name.lower() == 'nan':
                continue
            
            # Get second column as candidate skills
            candidate_skills_raw = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
            
            # Calculate match score using embedding similarity
            if not candidate_skills_raw or candidate_skills_raw.lower() == 'none' or candidate_skills_raw.lower() == 'nan':
                score = 0
                status = 'No Skills'
            else:
                try:
                    candidate_embedding = get_embedding(candidate_skills_raw)
                    score = calculate_embedding_similarity(required_embedding, candidate_embedding)
                    if score >= 70:
                        status = 'Excellent Match'
                    elif score >= 50:
                        status = 'Good Match'
                    elif score >= 30:
                        status = 'Partial Match'
                    else:
                        status = 'Low Match'
                except Exception as e:
                    score = 0
                    status = 'Error'
            
            results.append({
                'name': candidate_name,
                'score': score,
                'status': status
            })
        
        return results
    except Exception as e:
        raise Exception(f'Error parsing Excel file: {str(e)}')

def parse_csv_file(csv_file, required_skills_list):
    """
    Parse CSV file and analyze candidate skills using OpenAI embeddings
    """
    results = []
    try:
        # Read CSV file using pandas
        df = pd.read_csv(csv_file)
        
        # Get embeddings for required skills as plain text
        required_skills_str = ", ".join(required_skills_list)
        required_embedding = get_embedding(required_skills_str)
        
        # Process each row
        for idx, row in df.iterrows():
            # Get first column as candidate name
            candidate_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            
            if not candidate_name or candidate_name.lower() == 'nan':
                continue
            
            # Get second column as candidate skills
            candidate_skills_raw = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
            
            # Calculate match score using embedding similarity
            if not candidate_skills_raw or candidate_skills_raw.lower() == 'none' or candidate_skills_raw.lower() == 'nan':
                score = 0
                status = 'No Skills'
            else:
                try:
                    candidate_embedding = get_embedding(candidate_skills_raw)
                    score = calculate_embedding_similarity(required_embedding, candidate_embedding)
                    if score >= 70:
                        status = 'Excellent Match'
                    elif score >= 50:
                        status = 'Good Match'
                    elif score >= 30:
                        status = 'Partial Match'
                    else:
                        status = 'Low Match'
                except Exception as e:
                    score = 0
                    status = 'Error'
            
            results.append({
                'name': candidate_name,
                'score': score,
                'status': status
            })
        
        return results
    except Exception as e:
        raise Exception(f'Error parsing CSV file: {str(e)}')


# ============================================================================
# EMBEDDING & SIMILARITY FUNCTIONS (OpenAI API Integration)
# ============================================================================

def get_embedding(text):
    """
    Get embedding from OpenAI API with retry logic and connection diagnostics.
    Prefers the initialized openai_client when available; falls back to manual requests.
    """
    # try using client if initialized
    if openai_client:
        try:
            print(f"🔄 Generating embedding via openai_client for text: '{text[:50]}...'")
            resp = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            embedding = resp.data[0].embedding
            print(f"✅ Got embedding from client (length {len(embedding)})")
            return embedding
        except Exception as client_err:
            print(f"⚠️ openai_client embedding failed: {client_err}. Falling back to requests.")
            # continue to request-based path

    # Manual HTTP fallback (existing logic)
    print(f"🔄 Attempting to get embedding for text: '{text[:50]}...' (requests.post style)")
    url = f"{api_base.rstrip('/')}/embeddings"  # ensure single slash
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "model": EMBEDDING_MODEL,
        "input": text
    }
    max_attempts = 3
    delay = 1
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"📡 Attempt {attempt}/{max_attempts} - Calling: {url}")
            response = requests.post(url, headers=headers, json=data, verify=False)
            if response.status_code == 200:
                embedding = response.json()["data"][0]["embedding"]
                print(f"✅ Successfully got embedding! Length: {len(embedding)}")
                return embedding
            else:
                print(f"❌ API returned status {response.status_code}: {response.text}")
                raise Exception(f"API error: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {str(e)}")
            if attempt == max_attempts:
                err_str = str(e)
                print(f"🚫 All attempts failed. Final error: {err_str}")
                raise Exception(f"Error getting embedding: {err_str}")
            else:
                import time
                print(f"⏳ Waiting {delay} seconds before retry...")
                time.sleep(delay)
                delay *= 2
                continue

def calculate_embedding_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two embeddings
    Returns a score between 0 and 100
    """
    try:
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        cosine_sim = dot_product / (norm1 * norm2)
        
        # Convert to 0-100 scale
        score = max(0, min(100, int((cosine_sim + 1) / 2 * 100)))
        
        return score
    except Exception as e:
        raise Exception(f'Error calculating similarity: {str(e)}')

@csrf_exempt
def analyze_candidate_profile(request):
    """
    Analyze candidate profile (PDF or Word) and match with job skills
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Get job skills
        job_skills = request.POST.get('job_skills', '').strip()
        if not job_skills:
            return JsonResponse({'success': False, 'error': 'No job skills provided'})
        
        # Get candidate file
        candidate_file = request.FILES.get('candidate_file')
        if not candidate_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        # Extract text from file
        file_name = candidate_file.name.lower()
        if file_name.endswith('.pdf'):
            profile_text = extract_pdf_text(candidate_file)
        elif file_name.endswith(('.docx', '.doc')):
            profile_text = extract_word_text(candidate_file)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid file format. Please upload PDF or Word document.'})
        
        if not profile_text or len(profile_text.strip()) < 10:
            return JsonResponse({'success': False, 'error': 'Could not extract text from the document.'})
        
        # Analyze profile
        result = analyze_profile_match(profile_text, job_skills)
        
        return JsonResponse({'success': True, **result})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})

def extract_pdf_text(pdf_file):
    """
    Extract text from PDF file
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + " "
        return text
    except Exception as e:
        raise Exception(f'Error reading PDF: {str(e)}')

def extract_word_text(word_file):
    """
    Extract text from Word document
    """
    try:
        doc = Document(word_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + " "
        return text
    except Exception as e:
        raise Exception(f'Error reading Word document: {str(e)}')

def analyze_profile_match(profile_text, job_skills):
    """
    Analyze candidate profile and match with job skills using OpenAI embeddings
    """
    try:
        # Get embeddings
        # prepare plain-text inputs for embeddings
        job_skills_str = job_skills.replace('\n', ', ')
        job_embedding = get_embedding(job_skills_str)
        profile_excerpt = profile_text[:2000]
        profile_embedding = get_embedding(profile_excerpt)
        
        # Calculate similarity score
        match_score = calculate_embedding_similarity(job_embedding, profile_embedding)
        
        # Determine status
        if match_score >= 70:
            status = 'Excellent Match'
        elif match_score >= 50:
            status = 'Good Match'
        elif match_score >= 30:
            status = 'Moderate Match'
        else:
            status = 'Low Match'
        
        # Extract matching and missing skills
        job_skills_list = [skill.strip().lower() for skill in job_skills.replace('\n', ',').split(',') if skill.strip()]
        profile_lower = profile_text.lower()
        
        matching_skills = []
        missing_skills = []
        
        for skill in job_skills_list:
            if skill in profile_lower or any(word in skill for word in profile_lower.split() if len(word) > 4):
                matching_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        # Create profile summary
        profile_summary = profile_text[:500] + "..." if len(profile_text) > 500 else profile_text
        
        # Generate recommendation
        if match_score >= 70:
            recommendation = "This candidate is a strong match for the position. They have excellent alignment with the required skills and experience."
        elif match_score >= 50:
            recommendation = "This candidate is a good match. They have most of the required skills with some potential for learning and growth."
        elif match_score >= 30:
            recommendation = "This candidate has moderate compatibility. They have some relevant skills but may need training in additional areas."
        else:
            recommendation = "This candidate has limited match with the job requirements. Consider providing additional training or looking for candidates with stronger alignment."
        
        # preserve original job skills text for output
        job_skills_text = job_skills
        
        return {
            'match_score': match_score,
            'status': status,
            'job_skills': job_skills_text,
            'matching_skills': ', '.join(matching_skills) if matching_skills else 'None',
            'missing_skills': ', '.join(missing_skills) if missing_skills else 'All skills present',
            'profile_summary': profile_summary[:200] + "..." if len(profile_summary) > 200 else profile_summary,
            'recommendation': recommendation
        }
    except Exception as e:
        raise Exception(f'Error analyzing profile: {str(e)}')

def candidates(request):
    """Render candidates page"""
    return render(request, 'candidates.html')

@csrf_exempt
def analyze_candidates(request):
    """
    Analyze candidates based on skill, proficiency level, and experience
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Get filter criteria
        skill = request.POST.get('skill', '').strip()
        proficiency = request.POST.get('proficiency', '').strip()
        accrual = request.POST.get('accrual', '').strip()
        
        if not skill or not proficiency or not accrual:
            return JsonResponse({'success': False, 'error': 'All filter criteria must be selected'})
        
        # Get the uploaded file
        candidate_file = request.FILES.get('candidate_file')
        if not candidate_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        # Parse file
        file_name = candidate_file.name.lower()
        try:
            if file_name.endswith('.csv'):
                df = pd.read_csv(candidate_file)
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(candidate_file)
            else:
                return JsonResponse({'success': False, 'error': 'Invalid file format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error reading file: {str(e)}'})
        
        results = []
        
        # Process each candidate
        for idx, row in df.iterrows():
            candidate_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            
            if not candidate_name or candidate_name.lower() == 'nan':
                continue
            
            # Get candidate skills (column 2) and experience if available
            candidate_skills = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
            candidate_exp = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ''
            candidate_prof = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else ''
            
            if not candidate_skills:
                continue
            
            # Calculate scores using embedding similarity
            try:
                skill_match = calculate_skill_score(skill, candidate_skills)
                proficiency_match = calculate_proficiency_score(proficiency, candidate_prof)
                experience_match = calculate_experience_score(accrual, candidate_exp)
                
                results.append({
                    'name': candidate_name,
                    'skill_match': skill_match,
                    'proficiency_match': proficiency_match,
                    'experience_match': experience_match
                })
            except Exception as e:
                continue
        
        if not results:
            return JsonResponse({'success': False, 'error': 'No valid candidate data found'})
        
        return JsonResponse({'success': True, 'results': results})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})

def calculate_skill_score(required_skill, candidate_skills):
    """
    Calculate skill match score using embeddings
    """
    try:
        required_embedding = get_embedding(required_skill)
        candidate_embedding = get_embedding(candidate_skills)
        score = calculate_embedding_similarity(required_embedding, candidate_embedding)
        return score
    except:
        # Fallback to keyword matching if embedding fails
        required_skill_lower = required_skill.lower()
        candidate_skills_lower = candidate_skills.lower()
        
        if required_skill_lower in candidate_skills_lower or candidate_skills_lower in required_skill_lower:
            return 85
        elif any(skill in candidate_skills_lower for skill in required_skill_lower.split()):
            return 60
        return 30

def calculate_proficiency_score(required_proficiency, candidate_proficiency):
    """
    Calculate proficiency level match score
    """
    if not candidate_proficiency:
        return 30
    
    proficiency_levels = {'E0': 1, 'E1': 2, 'E2': 3, 'E3': 4}
    
    required_level = proficiency_levels.get(required_proficiency, 0)
    candidate_level = proficiency_levels.get(candidate_proficiency, 0)
    
    if required_level == candidate_level:
        return 100
    elif abs(required_level - candidate_level) == 1:
        return 75
    elif abs(required_level - candidate_level) == 2:
        return 50
    else:
        return 25

def calculate_experience_score(required_accrual, candidate_experience):
    """
    Calculate experience requirement match score
    """
    if not candidate_experience:
        return 30
    
    candidate_exp_lower = candidate_experience.lower()
    required_accrual_lower = required_accrual.lower()
    
    # Map experience to years
    exp_mapping = {
        'recent': 0.5,
        '0-6': 0.5,
        'months': 0.5,
        '1year': 1,
        '1': 1,
        '2years': 2,
        '2': 2,
        'more': 3,
        '3': 3,
        '5': 5,
        '10': 10
    }
    
    required_years = 0
    if 'recent' in required_accrual_lower:
        required_years = 0.5
    elif '1year' in required_accrual_lower or '1 year' in required_accrual_lower:
        required_years = 1
    elif '2years' in required_accrual_lower or '2 years' in required_accrual_lower:
        required_years = 2
    elif 'more' in required_accrual_lower:
        required_years = 3
    
    candidate_years = 0
    for key, value in exp_mapping.items():
        if key in candidate_exp_lower:
            candidate_years = value
            break
    
    if candidate_years == 0 and required_years > 0:
        return 30
    elif candidate_years >= required_years:
        return min(100, 70 + (candidate_years - required_years) * 10)
    else:
        return max(30, 70 - (required_years - candidate_years) * 20)


# ============================================================================
# RANKED CANDIDATE SHORTLIST & LEARNING PLAN FEATURES
# ============================================================================

def get_role_candidates_ranked(request, role=None):
    """
    Get ranked candidates for a specific role with match scores and rationale
    """
    try:
        # Define common roles and their required skills
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'key_skills': ['Cloud Cost Optimization', 'Performance Monitoring'],
                'proficiency_level': 'Intermediate'
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization', 'Infrastructure Monitoring'],
                'key_skills': ['CI/CD Pipelines', 'Docker', 'Container Optimization'],
                'proficiency_level': 'Intermediate'
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python', 'Performance Optimization'],
                'key_skills': ['Algorithm Optimization', 'Energy Efficient Coding'],
                'proficiency_level': 'Intermediate'
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python', 'Tableau', 'Power BI'],
                'key_skills': ['Data Analytics', 'ESG Reporting', 'SQL'],
                'proficiency_level': 'Intermediate'
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance', 'Infrastructure Monitoring'],
                'key_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure'],
                'proficiency_level': 'Intermediate'
            }
        }
        
        if not role:
            role = request.GET.get('role', 'Cloud Efficiency Engineer')
        
        role_req = ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS['Cloud Efficiency Engineer'])
        candidates = Candidate.objects.all()
        
        ranked_candidates = []
        
        for candidate in candidates:
            # Get candidate skills from skill_vectors
            candidate_skills = []
            if candidate.skill_vectors:
                candidate_skills = [s.get('skill', '').lower() for s in candidate.skill_vectors]
            
            # Calculate matched skills
            matched_skills = []
            missing_skills = []
            
            for req_skill in role_req['required_skills']:
                found = False
                for cand_skill in candidate_skills:
                    if req_skill.lower() in cand_skill or cand_skill in req_skill.lower():
                        matched_skills.append(req_skill)
                        found = True
                        break
                if not found:
                    missing_skills.append(req_skill)
            
            # Calculate match score (0-100)
            if len(role_req['required_skills']) > 0:
                match_score = (len(matched_skills) / len(role_req['required_skills'])) * 100
            else:
                match_score = 0
            
            # Get proficiency level bonus
            prof_bonus = 0
            if candidate.proficiency_level and candidate.proficiency_level.lower() == 'expert':
                prof_bonus = 10
            elif candidate.proficiency_level and candidate.proficiency_level.lower() == 'advanced':
                prof_bonus = 5
            
            final_score = min(100, match_score + prof_bonus)
            
            ranked_candidates.append({
                'candidate_name': candidate.candidate_name,
                'email': candidate.email,
                'phone': candidate.phone,
                'current_role': candidate.current_role,
                'grade': candidate.grade,
                'employment_type': candidate.employment_type,
                'match_score': round(final_score, 1),
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'proficiency_level': candidate.proficiency_level,
                'skill_vectors': candidate.skill_vectors or []
            })
        
        # Sort by match score descending
        ranked_candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Get available roles
        available_roles = list(ROLE_REQUIREMENTS.keys())
        
        context = {
            'ranked_candidates': ranked_candidates,
            'selected_role': role,
            'available_roles': available_roles,
            'top_candidates': ranked_candidates[:10]  # Top 10 candidates
        }
        
        return render(request, 'candidate_shortlist.html', context)
    
    except Exception as e:
        print(f"Error in get_role_candidates_ranked: {e}")
        import traceback
        traceback.print_exc()
        return render(request, 'candidate_shortlist.html', {'error': str(e)})


def get_candidate_learning_plan(request, candidate_id=None):
    """
    Generate learning plan for a candidate based on role requirements
    """
    try:
        role = request.GET.get('role', 'Cloud Efficiency Engineer')
        candidate_name = request.GET.get('candidate_name', '')
        
        if not candidate_name:
            return JsonResponse({'success': False, 'error': 'Candidate name required'})
        
        # Get candidate from DB
        try:
            candidate = Candidate.objects.get(candidate_name=candidate_name)
        except Candidate.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Candidate not found'})
        
        # Role requirements
        ROLE_REQUIREMENTS = {
            'Cloud Efficiency Engineer': {
                'required_skills': ['Cloud Cost Optimization', 'Performance Monitoring', 'FinOps', 'AWS', 'Azure'],
                'proficiency_levels': {'Cloud Cost Optimization': 'Expert', 'Performance Monitoring': 'Intermediate', 'FinOps': 'Intermediate'}
            },
            'Green DevOps Engineer': {
                'required_skills': ['CI/CD Pipelines', 'Docker', 'Kubernetes', 'Container Optimization'],
                'proficiency_levels': {'CI/CD Pipelines': 'Expert', 'Docker': 'Expert', 'Container Optimization': 'Intermediate'}
            },
            'Sustainable Software Engineer': {
                'required_skills': ['Algorithm Optimization', 'Energy Efficient Coding', 'Python'],
                'proficiency_levels': {'Algorithm Optimization': 'Expert', 'Energy Efficient Coding': 'Intermediate', 'Python': 'Expert'}
            },
            'ESG Data Analyst': {
                'required_skills': ['Data Analytics', 'ESG Reporting', 'SQL', 'Python'],
                'proficiency_levels': {'Data Analytics': 'Expert', 'ESG Reporting': 'Intermediate', 'SQL': 'Intermediate'}
            },
            'Green IT Specialist': {
                'required_skills': ['Sustainable IT Practices', 'Energy Efficient Infrastructure', 'IT Governance'],
                'proficiency_levels': {'Sustainable IT Practices': 'Expert', 'Energy Efficient Infrastructure': 'Intermediate', 'IT Governance': 'Basic'}
            }
        }
        
        role_req = ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS['Cloud Efficiency Engineer'])
        
        # Get candidate current skills
        current_skills = {}
        if candidate.skill_vectors:
            for skill in candidate.skill_vectors:
                current_skills[skill.get('skill', '')] = {
                    'proficiency': skill.get('proficiency_level', 'Basic'),
                    'score': skill.get('skill_level_score', 0)
                }
        
        # Build learning plan
        learning_plan = []
        gap_count = 0
        
        for req_skill in role_req['required_skills']:
            required_prof = role_req['proficiency_levels'].get(req_skill, 'Intermediate')
            
            if req_skill in current_skills:
                current_prof = current_skills[req_skill]['proficiency']
                current_score = current_skills[req_skill]['score']
                
                # Check if proficiency needs improvement
                prof_levels = {'Basic': 1, 'Intermediate': 2, 'Advanced': 3, 'Expert': 4}
                req_level = prof_levels.get(required_prof, 2)
                curr_level = prof_levels.get(current_prof, 1)
                
                if curr_level < req_level:
                    gap_count += 1
                    learning_plan.append({
                        'skill': req_skill,
                        'status': 'improvement_needed',
                        'current_level': current_prof,
                        'required_level': required_prof,
                        'current_score': current_score,
                        'gap': req_level - curr_level,
                        'duration': f'{(req_level - curr_level) * 2}-{(req_level - curr_level) * 4} weeks'
                    })
                else:
                    learning_plan.append({
                        'skill': req_skill,
                        'status': 'proficient',
                        'current_level': current_prof,
                        'required_level': required_prof,
                        'current_score': current_score,
                        'gap': 0,
                        'duration': 'Ready'
                    })
            else:
                gap_count += 1
                learning_plan.append({
                    'skill': req_skill,
                    'status': 'new_skill',
                    'current_level': 'None',
                    'required_level': required_prof,
                    'current_score': 0,
                    'gap': 3,
                    'duration': '8-12 weeks'
                })
        
        # Calculate readiness percentage
        readiness = ((len(learning_plan) - gap_count) / len(learning_plan)) * 100 if learning_plan else 0
        
        result = {
            'success': True,
            'candidate_name': candidate.candidate_name,
            'role': role,
            'current_role': candidate.current_role,
            'email': candidate.email,
            'readiness_percentage': round(readiness, 1),
            'learning_plan': learning_plan,
            'gap_count': gap_count,
            'total_skills': len(learning_plan)
        }
        
        return JsonResponse(result)
    
    except Exception as e:
        print(f"Error in get_candidate_learning_plan: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})