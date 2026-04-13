================================================================================
  StudySync — Cloud-Native Study Session Management Application
================================================================================

CONTENTS OF THIS FILE
----------------------
  1. Project Overview
  2. Repository Structure
  3. Dependencies
  4. Environment Variables & Configuration Files
  5. Local Development Setup
  6. AWS Infrastructure Setup
  7. Deployment to AWS EC2 (Production)
  8. studytimer_analytics Library — Installation & Usage
  9. Running Tests & Coverage
 10. Application URL Reference
 11. AWS SNS Topics & Notification Events
 12. Security Notes
 13. Troubleshooting


================================================================================
1. PROJECT OVERVIEW
================================================================================

StudySync is a cloud-based study timer and session management web application.
It allows students to:
  - Track timed study sessions with an optional subject tag
  - Monitor daily and weekly progress against configurable personal goals
  - Receive real-time email notifications via AWS Simple Notification Service (SNS)
  - View daily and weekly reports as Chart.js bar charts
  - Browse paginated, filterable session history

Tech Stack:
  Backend      : Django 4.2.16, Python 3.13
  Database     : SQLite (local dev / EC2 deployment) OR AWS RDS PostgreSQL
  Frontend     : Django Templates, Bootstrap 5, Chart.js
  Custom Lib   : studytimer_analytics (local pip-installable package)
  Notifications: AWS SNS (boto3)
  Hosting      : AWS EC2 (Amazon Linux 2, eu-west-1)
  WSGI Server  : Gunicorn 21.2.0
  Region       : eu-west-1 (Ireland) — GDPR data residency (NFR-14)


================================================================================
2. REPOSITORY STRUCTURE
================================================================================

studysync/
├── studysync/                  # Django project package
│   ├── __init__.py
│   ├── settings.py             # All Django settings (env-var driven)
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI entry point for Gunicorn
│
├── timer/                      # Main Django application
│   ├── __init__.py
│   ├── admin.py                # Django admin registration
│   ├── apps.py                 # AppConfig
│   ├── forms.py                # RegisterForm, ProfileForm, SessionStartForm
│   ├── models.py               # StudySession, UserProfile (ORM models)
│   ├── sns_service.py          # AWS SNS publish functions (boto3)
│   ├── urls.py                 # App-level URL patterns
│   └── views.py                # All Django views (CRUD, reports, admin)
│
├── studytimer_analytics/       # Custom pip-installable Python library
│   ├── __init__.py             # Package init — exports all 4 classes
│   ├── timers.py               # SessionTimer class
│   ├── aggregators.py          # ReportAggregator class
│   ├── formatters.py           # DurationFormatter class
│   └── evaluators.py           # StudyGoalEvaluator class
│
├── templates/                  # Django HTML templates (Bootstrap 5)
│   ├── base.html               # Base layout with nav, messages, CSS/JS
│   ├── registration/
│   │   ├── login.html          # Login page
│   │   └── register.html       # Registration page
│   └── timer/
│       ├── dashboard.html      # Live timer + session controls
│       ├── session_history.html # Paginated session log
│       ├── daily_report.html   # Daily Chart.js bar chart
│       ├── weekly_report.html  # Weekly Chart.js bar chart
│       ├── profile.html        # Goal settings + notification opt-in
│       ├── admin_users.html    # Staff: all users + stats
│       └── admin_stats.html    # Staff: system-level stats
│
├── static/
│   ├── css/main.css            # Custom CSS overrides
│   └── js/main.js              # Timer polling + Chart.js helpers
│
├── tests/
│   ├── __init__.py
│   └── test_analytics.py       # pytest unit tests for studytimer_analytics
│
├── manage.py                   # Django management CLI
├── Procfile                    # Gunicorn startup command
├── requirements.txt            # All Python dependencies
├── pytest.ini                  # pytest + coverage configuration
├── .env.example                # Environment variable template (copy to .env)
└── readme.txt                  # This file


================================================================================
3. DEPENDENCIES
================================================================================

All dependencies are listed in requirements.txt. Install with:

    pip install -r requirements.txt

--- Python Version ---
Python 3.13 (required)
Download: https://www.python.org/downloads/release/python-3130/

--- Core Dependencies ---
Django==4.2.16
    Django web framework (LTS release).
    https://docs.djangoproject.com/en/4.2/

gunicorn==21.2.0
    Production WSGI HTTP server for Python.
    https://gunicorn.org/

--- Database ---
psycopg2-binary==2.9.9
    PostgreSQL adapter for Python (required for AWS RDS deployment).
    Not required for SQLite-only local development but included for compatibility.
    https://pypi.org/project/psycopg2-binary/

--- AWS SDK ---
boto3==1.34.0
    Amazon Web Services SDK for Python.
    Used for SNS publish operations.
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

django-storages==1.14.2
    Django storage backends for AWS S3.
    Required only if USE_S3=True in environment.
    https://django-storages.readthedocs.io/

--- Testing & Linting ---
pytest==7.4.4
    Python testing framework.

pytest-django==4.7.0
    Django plugin for pytest (provides --ds flag and db fixtures).

pytest-cov==4.1.0
    Coverage plugin for pytest.
    Measures line coverage of studytimer_analytics library.

flake8==7.0.0
    Python code style checker (PEP 8 compliance).
    Max line length: 120 characters (see setup.cfg / pytest.ini).

--- studytimer_analytics Library ---
The custom analytics library has NO external dependencies beyond the Python
standard library. It does import from Django ORM inside ReportAggregator
methods, but only at call-time (lazy import), so the library itself can be
installed and its classes instantiated without Django being configured.

    Local installation (editable):
        pip install -e .

    (Run from inside the studysync/ directory where the library folder lives.)


================================================================================
4. ENVIRONMENT VARIABLES & CONFIGURATION FILES
================================================================================

All sensitive values are driven by environment variables. NEVER commit real
credentials to version control.

--- Step 1: Copy the example file ---

    cp .env.example .env

--- Step 2: Edit .env with real values ---

Below is a description of every variable:

VARIABLE                    REQUIRED   DESCRIPTION
--------------------------  ---------  ------------------------------------------
SECRET_KEY                  YES        Django secret key. Generate with:
                                       python -c "from django.core.management.utils
                                       import get_random_secret_key;
                                       print(get_random_secret_key())"

DEBUG                       YES        Set to False in production. True for local.

ALLOWED_HOSTS               YES        Comma-separated hostnames/IPs Django will
                                       serve. Example (EC2):
                                       ec2-xx-xx-xx-xx.eu-west-1.compute.amazonaws.com
                                       Example (local): localhost,127.0.0.1

RDS_DB_NAME                 NO*        PostgreSQL database name.
RDS_USERNAME                NO*        PostgreSQL username.
RDS_PASSWORD                NO*        PostgreSQL password.
RDS_HOSTNAME                NO*        RDS endpoint hostname. If this variable is
                                       NOT set, Django falls back to SQLite.
RDS_PORT                    NO*        PostgreSQL port (default: 5432).
                                       * Required only for RDS deployment.

AWS_ACCESS_KEY_ID           NO**       IAM access key for boto3 SNS calls.
AWS_SECRET_ACCESS_KEY       NO**       IAM secret key for boto3 SNS calls.
                                       ** Preferred alternative: attach an IAM
                                       role to the EC2 instance. If a role is
                                       attached, boto3 picks up credentials
                                       automatically and these vars are not needed.

AWS_SNS_REGION              YES        AWS region for SNS. Must be: eu-west-1

SNS_STUDENT_TOPIC_ARN       YES        Full ARN of the student notifications SNS
                                       topic. Example:
                                       arn:aws:sns:eu-west-1:123456789012:studysync-student-notifications

SNS_ADMIN_TOPIC_ARN         YES        Full ARN of the admin alerts SNS topic.
                                       Example:
                                       arn:aws:sns:eu-west-1:123456789012:studysync-admin-alerts

USE_S3                      NO         Set to True to serve static/media from S3.
                                       Default: False (local file system).

AWS_STORAGE_BUCKET_NAME     NO         S3 bucket name (required if USE_S3=True).
AWS_S3_REGION_NAME          NO         S3 region (default: eu-west-1).


--- Procfile ---
The Procfile defines the Gunicorn startup command:

    web: gunicorn studysync.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60

This is used automatically by Elastic Beanstalk and can be used manually on EC2.

--- pytest.ini ---
Configures pytest for Django:

    [pytest]
    DJANGO_SETTINGS_MODULE = studysync.settings
    python_files = tests/test_*.py
    addopts = --cov=studytimer_analytics --cov-report=term-missing

Run tests with:

    pytest tests/ -v


================================================================================
5. LOCAL DEVELOPMENT SETUP
================================================================================

Prerequisites:
  - Python 3.13 installed and on PATH
  - pip (bundled with Python 3.13)
  - Git (optional, for cloning)

Step 1 — Create and activate a virtual environment:

    python3.13 -m venv venv
    source venv/bin/activate          # macOS / Linux
    venv\Scripts\activate             # Windows

Step 2 — Install Python dependencies:

    pip install -r requirements.txt

Step 3 — Install the analytics library in editable mode:

    pip install -e .

    This installs studytimer_analytics as a local package so Django can
    import it with: from studytimer_analytics.timers import SessionTimer

Step 4 — Configure environment variables:

    cp .env.example .env
    # Edit .env — at minimum set SECRET_KEY and DEBUG=True
    # Leave RDS_* variables blank to use SQLite for local development
    # Leave SNS_*_TOPIC_ARN blank to disable notifications locally

Step 5 — Apply database migrations:

    python manage.py migrate

    This creates the SQLite database file (db.sqlite3) in the project root
    and applies all migrations for the timer app (StudySession, UserProfile).

Step 6 — Create a superuser (admin account):

    python manage.py createsuperuser

    Follow the prompts to set username, email, and password.
    Staff/superuser accounts can access the admin views at /admin-panel/users/

Step 7 — Collect static files (optional for development):

    python manage.py collectstatic --noinput

Step 8 — Start the development server:

    python manage.py runserver

    Open: http://localhost:8000
    Admin: http://localhost:8000/admin/ (Django built-in admin)

NOTE: The live timer AJAX polling and SNS notifications function in local
development. SNS publish calls will be silently skipped if SNS_STUDENT_TOPIC_ARN
and SNS_ADMIN_TOPIC_ARN are not set (the _publish() function returns False and
logs a warning — it does not raise an exception).


================================================================================
6. AWS INFRASTRUCTURE SETUP
================================================================================

All resources must be provisioned in eu-west-1 (Ireland) region (NFR-14 / GDPR).

--- 6.1 EC2 Instance ---

1. Launch an Amazon EC2 t2.micro instance:
   - AMI:    Amazon Linux 2 (ami-0fe0b2cf0e1f25c8a or latest AL2)
   - Region: eu-west-1
   - Key pair: create or select an existing key pair for SSH access

2. Security Group — inbound rules:
   - Port 22   (SSH)   — your IP only
   - Port 8000 (HTTP)  — 0.0.0.0/0 (or restrict to your IP for testing)
   - Port 443  (HTTPS) — 0.0.0.0/0 (if using an SSL/TLS termination proxy)

3. Connect via SSH:
   ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>

--- 6.2 IAM Role for EC2 (Recommended) ---

Create an IAM Role with the following inline policy and attach it to the EC2
instance. This is more secure than using long-lived access keys.

Policy document (replace ACCOUNT_ID and TOPIC_ARNS):

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "sns:Publish",
          "Resource": [
            "arn:aws:sns:eu-west-1:ACCOUNT_ID:studysync-student-notifications",
            "arn:aws:sns:eu-west-1:ACCOUNT_ID:studysync-admin-alerts"
          ]
        }
      ]
    }

Steps:
  1. AWS Console → IAM → Roles → Create role
  2. Trusted entity type: AWS service → EC2
  3. Attach the inline policy above
  4. Name the role: StudySyncEC2Role
  5. EC2 Console → Select instance → Actions → Security → Modify IAM role
  6. Attach StudySyncEC2Role

When an IAM role is attached, boto3 picks up credentials automatically via
the EC2 instance metadata service. Do NOT set AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY in the environment when using a role.

--- 6.3 AWS SNS Topics ---

Create two Standard SNS topics in eu-west-1:

Topic 1 — Student notifications:
  1. SNS Console → Topics → Create topic
  2. Type: Standard
  3. Name: studysync-student-notifications
  4. Copy the Topic ARN — set as SNS_STUDENT_TOPIC_ARN environment variable

Topic 2 — Admin alerts:
  1. SNS Console → Topics → Create topic
  2. Type: Standard
  3. Name: studysync-admin-alerts
  4. Copy the Topic ARN — set as SNS_ADMIN_TOPIC_ARN environment variable

Subscribe email addresses:
  1. Select the topic → Subscriptions → Create subscription
  2. Protocol: Email
  3. Endpoint: student or admin email address
  4. Confirm the subscription from the confirmation email received

--- 6.4 SQLite Database (EC2 deployment) ---

SQLite requires no additional AWS setup. The database file db.sqlite3 is
created automatically on first migration and stored on the EC2 EBS root volume.

For production scalability, swap to AWS RDS PostgreSQL by setting the RDS_*
environment variables (see Section 4). The settings.py automatically switches
to PostgreSQL when RDS_HOSTNAME is set.


================================================================================
7. DEPLOYMENT TO AWS EC2 (PRODUCTION)
================================================================================

Perform these steps on the EC2 instance after SSH connection.

--- 7.1 Prepare the EC2 Instance (first-time only) ---

    # Update system packages
    sudo yum update -y

    # Install Python 3.13
    sudo yum install -y openssl-devel bzip2-devel libffi-devel gcc make
    cd /tmp
    wget https://www.python.org/ftp/python/3.13.0/Python-3.13.0.tgz
    tar xzf Python-3.13.0.tgz
    cd Python-3.13.0
    ./configure --enable-optimizations
    make altinstall
    python3.13 --version     # Verify: Python 3.13.0

    # Install Git
    sudo yum install -y git

--- 7.2 Clone the Repository ---

    cd /home/ec2-user
    git clone https://github.com/YOUR_USERNAME/studysync.git
    cd studysync

--- 7.3 Create Virtual Environment and Install Dependencies ---

    python3.13 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .

--- 7.4 Set Environment Variables ---

Set variables in the EC2 instance environment. The recommended approach is to
add them to /home/ec2-user/.bashrc or use a .env file loaded by the application.

Option A — Export in shell (session-persistent only):

    export SECRET_KEY="your-very-long-random-secret-key"
    export DEBUG="False"
    export ALLOWED_HOSTS="ec2-xx-xx-xx-xx.eu-west-1.compute.amazonaws.com,localhost"
    export AWS_SNS_REGION="eu-west-1"
    export SNS_STUDENT_TOPIC_ARN="arn:aws:sns:eu-west-1:ACCOUNT_ID:studysync-student-notifications"
    export SNS_ADMIN_TOPIC_ARN="arn:aws:sns:eu-west-1:ACCOUNT_ID:studysync-admin-alerts"

Option B — .env file (recommended for persistence):

    cp .env.example .env
    nano .env          # Fill in all required values
    # Django picks up .env automatically via python-dotenv if configured,
    # or source it manually: set -a; source .env; set +a

--- 7.5 Apply Database Migrations ---

    python manage.py migrate

--- 7.6 Create Superuser ---

    python manage.py createsuperuser

--- 7.7 Collect Static Files ---

    python manage.py collectstatic --noinput

--- 7.8 Start Gunicorn ---

    gunicorn studysync.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --timeout 60 \
        --daemon \
        --access-logfile /home/ec2-user/gunicorn-access.log \
        --error-logfile  /home/ec2-user/gunicorn-error.log

    Open: http://<EC2_PUBLIC_IP>:8000

--- 7.9 Subsequent Deployments (code updates) ---

    cd /home/ec2-user/studysync
    source venv/bin/activate
    git pull origin main
    pip install -r requirements.txt
    pip install -e .
    python manage.py migrate
    python manage.py collectstatic --noinput
    pkill gunicorn
    gunicorn studysync.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --timeout 60 \
        --daemon \
        --access-logfile /home/ec2-user/gunicorn-access.log \
        --error-logfile  /home/ec2-user/gunicorn-error.log

--- 7.10 Verify Deployment ---

    curl http://localhost:8000/accounts/login/
    # Should return HTTP 200 with login page HTML


================================================================================
8. studytimer_analytics LIBRARY — INSTALLATION & USAGE
================================================================================

The studytimer_analytics package is a local pip-installable library that
encapsulates all session computation, aggregation, formatting, and goal
evaluation logic for StudySync.

--- Installation ---

From within the studysync/ project directory:

    pip install -e .

The -e flag installs the package in editable (development) mode, meaning
changes to the source files are reflected immediately without reinstalling.

--- Classes ---

1. SessionTimer (studytimer_analytics.timers)
   -----------------------------------------------
   Calculates elapsed time and session state for a study session.

   Usage:
       from studytimer_analytics.timers import SessionTimer
       from datetime import datetime, timezone

       timer = SessionTimer(started_at=session.started_at)
       print(timer.elapsed_seconds())   # e.g. 3600
       print(timer.format_hms())        # e.g. "01:00:00"
       print(timer.is_active())         # True (no ended_at supplied)

   Methods:
       elapsed_seconds() -> int     : Total elapsed seconds
       elapsed_minutes() -> float   : Total elapsed minutes (fractional)
       format_hms()      -> str     : Zero-padded HH:MM:SS string
       is_active()       -> bool    : True if session has no end time
       started_at()      -> datetime: UTC start datetime
       ended_at()        -> datetime|None: UTC end datetime or None


2. ReportAggregator (studytimer_analytics.aggregators)
   -----------------------------------------------
   Computes daily and weekly study session aggregates for a user.

   Usage:
       from studytimer_analytics.aggregators import ReportAggregator
       from datetime import date

       agg = ReportAggregator(user=request.user)
       daily  = agg.daily_report(date.today())
       weekly = agg.weekly_report(date.today())

   daily_report(report_date) returns:
       {
         "total_seconds"      : int,
         "session_count"      : int,
         "avg_session_seconds": int,
         "subject_breakdown"  : {subject: seconds, ...}
       }

   weekly_report(end_date) returns all keys above plus:
       {
         "days_studied"  : int,
         "current_streak": int,
         "daily_labels"  : ["Mon 07/04", ...],   # 7 items
         "daily_totals"  : [seconds, ...]         # 7 items (Chart.js ready)
       }


3. DurationFormatter (studytimer_analytics.formatters)
   -----------------------------------------------
   Converts raw seconds / minutes into human-readable strings.

   Usage:
       from studytimer_analytics.formatters import DurationFormatter

       fmt = DurationFormatter()
       fmt.format_duration(7530)   # "2 hr 5 min 30 sec"
       fmt.format_hms(7530)        # "02:05:30"
       fmt.format_minutes(125)     # "125 min"


4. StudyGoalEvaluator (studytimer_analytics.evaluators)
   -----------------------------------------------
   Evaluates goal attainment and drives SNS notification dispatch.

   Usage:
       from studytimer_analytics.evaluators import StudyGoalEvaluator

       evaluator = StudyGoalEvaluator(
           minutes_studied=130,
           goal_minutes=profile.daily_goal_minutes
       )
       print(evaluator.is_goal_achieved())   # True (130 >= 120)
       print(evaluator.progress_percent())   # 100.0 (capped)
       print(evaluator.remaining_minutes())  # 0
       result = evaluator.evaluate()
       # {"achieved": True, "progress_percent": 100.0, "remaining_minutes": 0}


================================================================================
9. RUNNING TESTS & COVERAGE
================================================================================

Run the full test suite with coverage report:

    pytest tests/ -v --cov=studytimer_analytics --cov-report=term-missing

Expected output:
  - All tests PASSED
  - Coverage >= 70% for each module in studytimer_analytics (NFR-10)
  - Current achieved coverage: approximately 89% overall

Run linting (PEP 8 compliance):

    flake8 timer/ studytimer_analytics/ tests/ --max-line-length=120

Run individual test file:

    pytest tests/test_analytics.py -v


================================================================================
10. APPLICATION URL REFERENCE
================================================================================

URL                          VIEW                    DESCRIPTION
---------------------------  ----------------------  ----------------------------
/                            redirect → /dashboard/  Root redirect
/accounts/login/             login_view              Login page
/accounts/logout/            Django built-in         Logout
/register/                   register_view           New user registration
/dashboard/                  dashboard               Live timer dashboard
/session/start/              start_session           POST: start study session
/session/stop/               stop_session            POST: stop active session
/session/delete/<pk>/        delete_session          POST: delete a session
/session/status/             session_status          AJAX: timer status JSON
/reports/daily/              daily_report            Daily Chart.js report
/reports/weekly/             weekly_report           Weekly Chart.js report
/history/                    session_history         Paginated session log
/profile/                    profile_view            Goal & notification settings
/admin-panel/users/          admin_users             Staff: all users (is_staff)
/admin-panel/stats/          admin_stats             Staff: system stats
/admin/                      Django admin            Built-in model admin


================================================================================
11. AWS SNS TOPICS & NOTIFICATION EVENTS
================================================================================

Two SNS Standard Topics are used (both in eu-west-1):

  studysync-student-notifications
    Subscribers: student email addresses (subscribed on registration)
    Events:
      - Session started         (FR-12, FR-04)
      - Session completed       (FR-06, FR-12)
      - Daily goal achieved     (FR-12)
      - Weekly goal achieved    (FR-12)

  studysync-admin-alerts
    Subscribers: administrator email address(es)
    Events:
      - Critical application error  (NFR-07)
      - Environment health degraded (NFR-07)

All SNS publish calls are wrapped in try/except. Failures are logged at ERROR
level but do not raise exceptions or return HTTP error responses (NFR-07).

Users can opt out of notifications by unchecking "Receive SNS Notifications"
in their profile settings page (/profile/). This sets the
UserProfile.sns_notifications_enabled flag to False and all _should_notify()
checks will return False, silencing all SNS calls for that user (FR-11).


================================================================================
12. SECURITY NOTES
================================================================================

  - SECRET_KEY must be a long, random string. Never commit it to source control.
  - DEBUG must be False in production to prevent stack trace exposure.
  - ALLOWED_HOSTS must list only the EC2 public DNS / IP in production.
  - Passwords are hashed with PBKDF2-SHA256 (Django default, 720,000 iterations).
  - All views use @login_required decorator (NFR-03).
  - All ORM queries filter by user=request.user to enforce data isolation (NFR-03).
  - Session termination uses transaction.atomic() to prevent partial writes (NFR-08).
  - IAM credentials should use a role (not long-lived keys) where possible.
  - IAM policy grants only sns:Publish on the two specific topic ARNs (least privilege).
  - Production settings.py enables HTTPS redirect, HSTS, and secure cookies when
    DEBUG=False (NFR-06).
  - The .env file must be added to .gitignore. It is NOT included in this submission.


================================================================================
13. TROUBLESHOOTING
================================================================================

PROBLEM: "DisallowedHost" error on EC2
SOLUTION: Add the EC2 public DNS to ALLOWED_HOSTS environment variable.
          Example: export ALLOWED_HOSTS="ec2-xx-xx.eu-west-1.compute.amazonaws.com"

PROBLEM: SNS notifications not being sent
SOLUTION:
  1. Check SNS_STUDENT_TOPIC_ARN and SNS_ADMIN_TOPIC_ARN are set correctly.
  2. Verify the IAM role/user has sns:Publish permission on both topic ARNs.
  3. Ensure the AWS region is eu-west-1 (AWS_SNS_REGION=eu-west-1).
  4. Check gunicorn-error.log for SNS publish error messages.
  5. Confirm the user's SNS opt-in is enabled in /profile/.

PROBLEM: "No module named 'studytimer_analytics'"
SOLUTION: Run: pip install -e .  from inside the studysync/ directory.
          Ensure the virtual environment is activated.

PROBLEM: "relation does not exist" database error
SOLUTION: Run: python manage.py migrate
          This creates all required database tables.

PROBLEM: Static files not loading (CSS/JS 404)
SOLUTION: Run: python manage.py collectstatic --noinput
          Set STATIC_URL=/static/ in environment (default for local).

PROBLEM: Gunicorn port 8000 already in use
SOLUTION: Run: pkill gunicorn  then restart Gunicorn.

PROBLEM: Timer shows 0 on page load then jumps
SOLUTION: This is expected behaviour if the browser blocks the first AJAX call.
          The server-authoritative elapsed_seconds is embedded in the page HTML
          as a data attribute and is used as the seed value for the JS counter.

================================================================================
  End of readme.txt
  StudySync | MSc Cloud Computing | NCI | 2026
================================================================================
