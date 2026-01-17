# Resume Analyzer

## Intro
Resume Analyzer is a Django web app that helps job seekers analyze resumes and helps recruiters rank candidates. It includes separate flows for talent and recruiter roles and provides a guided UI for uploads, analysis, and results.

## How to Clone and Run
```bash
git clone <your-repo-url>
cd Resume_Analyzer

python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000 and http://localhost:8000/admin for admin access.

## UI Screenshots
![Home](screenshots/1_home.png)
![Loading](screenshots/2.5_loading.png)
![Home - Alternate](screenshots/2_home.png)
![Recruiter - Step 1](screenshots/3_recruiter.png)
![Recruiter - Step 2](screenshots/4_recruiter.png)
![Recruiter - Step 3](screenshots/5_recruiter.png)
![Recruiter - Step 4](screenshots/6_recruiter.png)
![Talent - Step 1](screenshots/7.5_talent.png)
![Talent - Step 2](screenshots/7_talent.png)
![Talent - Step 3](screenshots/8_talent.png)
![Talent - Step 4](screenshots/9_talent.png)
