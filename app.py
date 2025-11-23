import os
import json
import re
import hashlib
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv
import time
import smtplib
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer



# --- Load environment variables ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change_this_secret")

# --- Firebase initialization (safe) ---
try:
    import firebase_admin
    from firebase_admin import credentials, db

    cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-key.json")
    db_url = os.getenv("FIREBASE_DB_URL", None)
    if not db_url:
        raise ValueError("FIREBASE_DB_URL not set in .env")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})
        print("✅ Firebase connected successfully!")
    else:
        print("ℹ️ Firebase already initialized.")
except Exception as e:
    print(f"⚠️ Firebase initialization skipped or failed: {e}")
    firebase_admin = None
    db = None

# --------------------------
# --- AI backend import ---
# --------------------------
try:
    from backend.ai_recommendation import (
        generate_roadmap,
        generate_quiz,
        get_interview_question,
        get_interview_feedback,
        model  # optional; some functions use it
    )
    print("✅ AI backend imported.")
except Exception as e:
    print(f"⚠️ Warning: Could not import backend modules. Error: {e}")

    # Fallbacks (keep your original behavior)
    def generate_roadmap(career_path, skill_level):
        return {"roadmap": [{"week": "Weeks 1-2", "topics": "Intro to Python, Data Basics"}]}

    def generate_quiz(topic):
        return {"quiz": [
            {"question": "What is AI?", "options": ["Animal Intelligence", "Artificial Intelligence", "Analytical Input"], "answer": "Artificial Intelligence"}
        ]}

    def get_interview_question():
        return "Explain the difference between lists and tuples in Python."

    def get_interview_feedback(question, answer):
        return f"Feedback for '{question}': Your answer was okay, but you can add more technical details."

    model = None

# --------------------------
# --- Helpers -------------
# --------------------------

def uid_from_email(email: str) -> str:
    """Create safe uid from email (hash) to use as DB key."""
    if not email:
        return None
    h = hashlib.sha256(email.strip().lower().encode('utf-8')).hexdigest()
    return h[:28]  # short but unique





# ---------------------------------------------------
# 🔥 Recalculate Overall Progress (NEW HELPER)
# ---------------------------------------------------
def recompute_user_overall_progress(uid):
    if db is None or not uid:
        return

    try:
        resources = db.reference(f"users/{uid}/resources").get() or {}

        if not resources:
            db.reference(f"users/{uid}").update({"progress": 0})
            return

        total = len(resources)
        completed_sum = 0

        for item in resources.values():
            completed_sum += item.get("progress", 0)

        overall = round(completed_sum / total, 1)

        db.reference(f"users/{uid}").update({"progress": overall})
        print(f"📊 Overall progress updated: {overall}%")

    except Exception as e:
        print("❌ recompute progress error:", e)



# --------------------------
# --- Auth & Onboarding ---
# --------------------------

@app.route('/')
def landing():
    """Landing (welcome) page with Sign Up / Login links."""
    return render_template('landing.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Sign up user and save in Firebase Realtime DB (hashed password)"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            return render_template('signup.html', error="⚠️ Please fill all fields.")

        uid = uid_from_email(email)
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        user_data = {
            "name": name,
            "email": email,
            "password": hashed_pw,
            "career": "",
            "skill_level": "",
            "progress": 0,
            "xp": 0,
            "quiz_score": 0
        }

        try:
            if db is not None:
                db.reference(f"/users/{uid}").set(user_data)
                print(f"✅ New user saved: {email}")
            else:
                print("⚠️ Firebase DB not available; user skipped.")
        except Exception as e:
            print(f"❌ Error saving user to Firebase: {e}")
            return render_template('signup.html', error="⚠️ Could not save user (check server).")

        session['uid'] = uid
        session['email'] = email
        session['name'] = name
        return redirect(url_for('onboarding'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user by matching hashed password from DB"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            return render_template('login.html', error="⚠️ Please enter both email and password.")

        uid = uid_from_email(email)
        try:
            user = db.reference(f"/users/{uid}").get() if db is not None else None

            if not user:
                return render_template('login.html', error="❌ User not found. Please sign up first.")

            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            if user.get('password') != hashed_pw:
                return render_template('login.html', error="❌ Incorrect password.")

            # ✅ Success — log user in
            session['uid'] = uid
            session['email'] = email
            session['name'] = user.get('name')
            return redirect(url_for('onboarding'))

        except Exception as e:
            print(f"❌ Login error: {e}")
            return render_template('login.html', error="⚠️ Server error during login.")

    return render_template('login.html')
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        uid = uid_from_email(email)

        if db is None:
            return render_template('forgot_password.html',
                                   error="Server error")

        user = db.reference(f"/users/{uid}").get()

        if not user:
            return render_template('forgot_password.html',
                                   error="Email not registered")

        # Set temporary password
        temp_pw = "Code123@"
        hashed = hashlib.sha256(temp_pw.encode()).hexdigest()
        db.reference(f"/users/{uid}").update({"password": hashed})

        return render_template('forgot_password.html',
                               success=f"Temporary password: {temp_pw}")

    return render_template('forgot_password.html')


#@app.route('/login_session', methods=['POST'])
#def login_session():
    ""#"Create Flask session after Firebase login"""
    #try:
       # data = request.get_json()
        #id_token = data.get("idToken")

        # Verify the Firebase token
        #decoded_token = firebase_auth.verify_id_token(id_token)
        #uid = decoded_token['uid']

        # Save UID into session
        #session['uid'] = uid
        #print(f"✅ User {uid} logged in successfully")

        #return jsonify({"status": "success", "uid": uid})

    #except Exception as e:
        #print(f"🔥 Login session error: {e}")
        #return jsonify({"status": "error", "message": str(e)}), 401
@app.route('/logout')
def logout():
    """Clear session and redirect to login"""
    session.clear()
    return redirect('/login')



#@app.route('/logout')
#def logout():
    #session.clear()
    #return redirect(url_for('landing'))


@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """
    Onboarding: choose career and skill level.
    POST -> saves career & skill_level to user's DB record and generates roadmap (optional)
    """
    uid = session.get('uid')
    if request.method == 'POST':
        career = request.form.get('career', '').strip()
        skill = request.form.get('skill', '').strip()
            # ✅ Save the user's selections in session for later use (roadmap/dashboard)
        session['career'] = career
        session['skill_level'] = skill

        if not uid:
            return redirect(url_for('login'))
        try:
            if db is not None:
                db.reference(f"/users/{uid}").update({"career": career, "skill_level": skill})
            # optionally generate roadmap immediately and show on page
            # we'll call the existing generate_roadmap function via server
            roadmap = None
            try:
                roadmap = generate_roadmap(career, skill)
            except Exception as e:
                print(f"⚠️ Roadmap generation fallback: {e}")
            return render_template('onboarding_result.html', career=career, skill=skill, roadmap=roadmap)
        except Exception as e:
            print(f"❌ Onboarding save error: {e}")
            return render_template('onboarding.html', error="Could not save onboarding. Try again.")
    # GET -> show onboarding form (prefill if session user has data)
    pre = {}
    if uid and db is not None:
        try:
            pre_db = db.reference(f"/users/{uid}").get() or {}
            pre['name'] = pre_db.get('name')
            pre['career'] = pre_db.get('career', '')
            pre['skill'] = pre_db.get('skill_level', '')
        except Exception as e:
            print(f"⚠️ Onboarding prefill read error: {e}")
    return render_template('onboarding.html', pre=pre)


# --------------------------
# --- Resources, Quiz, Interview, Dashboard (preserve original logic) ---
# --------------------------

@app.route('/resources', methods=['GET', 'POST'])
def resources():
    """AI-powered + personalized learning resources by user career"""
    topic = None
    ai_resources = None
    user_career = "General"

    # Get current user career
    uid = session.get('uid')
    if uid and db is not None:
        user_data = db.reference(f"/users/{uid}").get() or {}
        user_career = user_data.get("career", "General")

    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        if topic:
            try:
                if model:
                    prompt = f"""
                    You are an expert learning mentor for a {user_career}.
                    Find the best FREE and trusted online resources for "{topic}".
                    Include:
                    - 🎥 3 YouTube tutorials with short descriptions
                    - 📘 2 free courses or tools (like Coursera, W3Schools, Kaggle, etc.)
                    - 💬 1 motivational learning message
                    Format clean HTML only (<h3>, <ul>, <li>, <a>, <p>), no markdown or CSS.
                    Keep it clear and beautiful.
                    """
                    response = model.generate_content(prompt)
                    ai_resources = response.text.strip()
                else:
                    ai_resources = "<p>AI model not available right now.</p>"
            except Exception as e:
                print(f"⚠️ AI Resource Error: {e}")
                ai_resources = "<p>Couldn't fetch AI resources right now.</p>"

    return render_template('resources.html', topic=topic, ai_resources=ai_resources, user_career=user_career)


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    """Dynamic Quiz Generator — based on user's chosen career path"""
    uid = session.get('uid')
    topic = request.args.get('topic', '').strip()

    # Get user career path from Firebase
    user_career = "General"
    if uid and db is not None:
        try:
            user_data = db.reference(f"/users/{uid}").get() or {}
            user_career = user_data.get("career", "General")
        except Exception as e:
            print(f"⚠️ Firebase read error for quiz: {e}")

    # If no topic is passed, use their chosen career (like DevOps Engineer)
    if not topic:
        topic = user_career

    quiz_data = []

    try:
        # Try using AI model for quiz generation
        if model:
            prompt = f"""
            You are a senior interviewer preparing a quiz for a {user_career}.
            Create 5 high-quality multiple-choice questions on {topic}.
            Each question must have 4 options and 1 correct answer.
            Focus only on real {user_career} concepts, tools, and workflows.
            Return JSON with this format:
            {{
              "quiz": [
                {{"question": "...", "options": ["A","B","C","D"], "answer": "A"}}
              ]
            }}
            """
            response = model.generate_content(prompt)
            import re, json
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                quiz_data = json.loads(match.group(0)).get("quiz", [])
        else:
            # fallback example if AI model is not available
            quiz_data = [
                {"question": f"What is CI/CD in {topic}?",
                 "options": ["Code Inspection", "Continuous Integration/Continuous Deployment", "Container Interface", "Cloud Input"],
                 "answer": "Continuous Integration/Continuous Deployment"},
                {"question": "Which tool is widely used for automation in DevOps?",
                 "options": ["Kubernetes", "Jenkins", "Figma", "Tableau"],
                 "answer": "Jenkins"},
                {"question": "Docker is used for?",
                 "options": ["Version Control", "Virtualization", "Containerization", "Monitoring"],
                 "answer": "Containerization"}
            ]
    except Exception as e:
        print(f"❌ Quiz generation error: {e}")

    return render_template('quiz.html', topic=topic, quiz_data=quiz_data)



@app.route('/interview')
def interview():
    """Mock interview page"""
    return render_template('interview.html')


@app.route('/dashboard')
def dashboard():
    """Smart Dashboard with XP and Badge System (loads logged-in user if present)"""

    # ✅ Add this block at the very beginning (session protection)
    if 'uid' not in session:
        return redirect('/login')

    uid = session.get('uid')
    user = None
    interview_preparedness = 0  # ✅ Initialize to avoid UnboundLocalError
    resources_completed = 0   

    uid = session.get('uid')
    user = None
    interview_preparedness = 0  # ✅ Initialize to avoid UnboundLocalError
    resources_completed = 0   

    if uid and db is not None:
        try:
            user_db = db.reference(f"/users/{uid}").get()
            if user_db:
                user = {
                    "name": user_db.get("name", "Guest"),
                    "stream": user_db.get("career", "N/A"),
                    "progress": user_db.get("progress", 0),
                    "quiz_score": user_db.get("quiz_score", 0),
                    "xp": user_db.get("xp", 0)
                }
        except Exception as e:
            print(f"⚠️ Firebase read error for dashboard: {e}")

    if not user:
        # fallback default user (same as your original)
        user = {
            "name": "Shraddha Repale",
            "stream": "Data Analyst",
            "progress": 70,
            "quiz_score": 85,
            "xp": 1520
        }

    # Save back the demo user if session exists (so you can see db update)
    try:
        if uid and db is not None and user:
            db.reference(f"/users/{uid}").update({
                "name": user["name"],
                "career": user["stream"],
                "progress": user["progress"],
                "quiz_score": user["quiz_score"],
                "xp": user["xp"]
            })
    except Exception as e:
        print(f"⚠️ Firebase write to dashboard failed: {e}")

    # Badge logic (unchanged)
    xp = user.get("xp", 0)
    if xp < 1000:
        badge = "🥉 Bronze Learner"; message = "Keep going — you're off to a great start!"
    elif xp < 2000:
        badge = "🥈 Silver Coder"; message = "Nice work! You're leveling up fast!"
    elif xp < 3500:
        badge = "🥇 Gold Achiever"; message = "Excellent consistency — you're becoming a pro!"
    else:
        badge = "💎 Diamond Master"; message = "Outstanding! You’re at the top of your learning journey!"

    # AI motivational tip (same behavior)
    try:
        if model:
            response = model.generate_content(
                f"Write one motivational sentence for a {user['stream']} student with {user['xp']} XP points."
            )
            ai_tip = response.text.strip()
        else:
            ai_tip = "Keep learning and challenging yourself daily!"
    except Exception:
        ai_tip = "Keep learning and challenging yourself daily!"
            # ------------------- Resource Progress Integration -------------------
    resources_completed = 0
    total_resources = 0

    try:
        if uid and db is not None:
            resources_data = db.reference(f"/users/{uid}/resources").get() or {}
            total_resources = len(resources_data)
            if total_resources > 0:
                completed = [r for r in resources_data.values() if r.get("progress", 0) == 100]
                resources_completed = round((len(completed) / total_resources) * 100, 1)
    except Exception as e:
        print(f"⚠️ Resource progress fetch error: {e}")
        resources_completed = 0
                # 🧠 Fetch interview preparedness score from Firebase
        interview_preparedness = 0
        try:
            if db is not None and 'uid' in session:
                uid = session['uid']
                prep_ref = db.reference(f"/users/{uid}/metrics/interview_preparedness")
                interview_preparedness = prep_ref.get() or 0
        except Exception as e:
            print(f"⚠️ Error loading interview preparedness: {e}")
            interview_preparedness = 0



    return render_template('dashboard.html', user=user, badge=badge, message=message, ai_tip=ai_tip,resources_completed=resources_completed,interview_preparedness=interview_preparedness)
@app.route('/chatbot')
def chatbot():
    """AI Chat Mentor Page"""
    
    return render_template('chatbot.html')




@app.route('/admin')
def admin():
    """Admin page to simulate leaderboard (temporary demo)"""
    sample_users = [
        {"name": "Alex", "xp": 15200, "streak": 32, "path": "AI/ML Engineer"},
        {"name": "Sarah", "xp": 14850, "streak": 28, "path": "Data Analyst"},
        {"name": "You (Sample)", "xp": 13550, "streak": 14, "path": "Data Analyst"},
        {"name": "David", "xp": 11200, "streak": 11, "path": "Backend Developer"}
    ]
    return render_template('admin.html', users=sample_users)


# --------------------------------------------------------------------
# -------------------------- API ENDPOINTS ---------------------------
# --------------------------------------------------------------------

@app.route('/generate-roadmap', methods=['GET', 'POST'])
def generate_roadmap_page():
    """Generate and display roadmap after onboarding"""
    try:
        # ✅ Use session or fallback to query parameters
        career_path = request.args.get('careerPath') or session.get('career')
        skill_level = request.args.get('skillLevel') or session.get('skill_level') or 'Beginner'

        # ✅ Fallback to Firebase if still missing
        if (not career_path) and ('uid' in session) and db is not None:
            user_data = db.reference(f"/users/{session['uid']}").get() or {}
            career_path = user_data.get("career") or "General"
            skill_level = user_data.get("skill_level") or "Beginner"

        # ✅ Default to "General" if all else fails
        if not career_path:
            career_path = "General"

        # Generate roadmap using AI model
        roadmap_result = generate_roadmap(career_path, skill_level)

        # Save last roadmap info (optional)
        if db is not None and 'uid' in session:
            db.reference(f"/users/{session['uid']}/last_roadmap").set({
                "careerPath": career_path,
                "skillLevel": skill_level
            })

        return render_template(
            'roadmap.html',
            career_path=career_path,
            skill_level=skill_level,
            roadmap=roadmap_result
        )

    except Exception as e:
        print(f"❌ Roadmap Page Error: {e}")
        return render_template(
            'roadmap.html',
            career_path=None,
            skill_level=None,
            roadmap={"error": "Could not generate roadmap."}
        )
@app.route('/week/<int:week_num>')
def week_page(week_num):
    """Display weekly progress, topics, and resource links"""
    uid = session.get('uid')
    if not uid:
        return redirect('/login')

    # Fetch roadmap data
    user_data = db.reference(f"/users/{uid}").get() or {}
    career = user_data.get("career", "General")
    roadmap = generate_roadmap(career, user_data.get("skill_level", "Beginner"))

    # Get topics for the selected week
    week_topics = []
    if roadmap and "roadmap" in roadmap:
        try:
            week_info = roadmap["roadmap"][week_num - 1]
            week_topics = week_info.get("topics", [])
        except Exception:
            week_topics = []

    return render_template("week.html", week_num=week_num, topics=week_topics, career=career)
    


@app.route('/generate-quiz', methods=['POST'])
def api_generate_quiz():
    """AI: Generate quiz questions"""
    try:
        data = request.json or {}
        topic = data.get('topic') or data.get('career') or "General"
        result = generate_quiz(topic)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Quiz Error: {e}")
        return jsonify({"error": "Failed to generate quiz"}), 500


@app.route('/get-interview-question', methods=['POST'])
def api_get_interview_question():
    """AI: Generate interview question specific to user's career path"""
    try:
        uid = session.get('uid')
        user_career = "General"
        if uid and db is not None:
            user_data = db.reference(f"/users/{uid}").get() or {}
            user_career = user_data.get("career", "General")

        if model:
            prompt = f"""
            You are an interviewer for the role of {user_career}.
            Ask one realistic technical interview question based on that role.
            The question should reflect real domain knowledge, not just general coding.
            """
            response = model.generate_content(prompt)
            question = response.text.strip()
        else:
            question = f"What is one important skill required for a {user_career}?"

        return jsonify({"question": question})
    except Exception as e:
        print(f"❌ Interview Question Error: {e}")
        return jsonify({"error": "Could not generate interview question"}), 500
    
@app.route('/get-interview-questions', methods=['POST'])
def get_interview_questions():
    """Generate 5 career-specific interview questions: 3 technical + 2 HR"""
    try:
        uid = session.get('uid')
        user_career = "General"
        if uid and db is not None:
            user_data = db.reference(f"/users/{uid}").get() or {}
            user_career = user_data.get("career", "General")

        if model:
            prompt = f"""
            You are an interviewer for the role of {user_career}.
            Ask exactly 5 interview questions:
            - 3 technical (increasing difficulty)
            - 2 HR or behavioral.
            Return valid JSON:
            {{
              "questions": [
                {{"type": "Technical", "question": "..." }},
                {{"type": "HR", "question": "..." }}
              ]
            }}
            """
            response = model.generate_content(prompt)
            import re, json
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            questions_data = json.loads(match.group(0))["questions"]
        else:
            questions_data = [
                {"type": "Technical", "question": "Explain overfitting in ML."},
                {"type": "Technical", "question": "What is normalization in SQL?"},
                {"type": "Technical", "question": "How do you optimize Python performance?"},
                {"type": "HR", "question": "Tell me about a time you faced a challenge."},
                {"type": "HR", "question": "Why should we hire you?"}
            ]

        return jsonify({"questions": questions_data})

    except Exception as e:
        print(f"❌ Mock Interview Generation Error: {e}")
        return jsonify({"error": "Could not generate questions"}), 500

   

@app.route('/get-interview-feedback', methods=['POST'])
def api_get_interview_feedback():
    """AI: Give personalized interview feedback & update XP/Progress dynamically"""
    try:
        uid = session.get('uid')
        user_career = "General"
        if uid and db is not None:
            user_data = db.reference(f"/users/{uid}").get() or {}
            user_career = user_data.get("career", "General")

        data = request.json or {}
        question = data.get('question', '')
        answer = data.get('answer', '')

        feedback = ""
        score = 0

        # 🧠 Generate real AI feedback
        if model:
            prompt = f"""
            You are an expert interviewer for a {user_career} role.
            Evaluate the following candidate answer carefully.

            Question: {question}
            Answer: {answer}

            Provide JSON output strictly in this format:
            {{
              "feedback": "Write your detailed constructive feedback",
              "score": 0–100
            }}
            """
            response = model.generate_content(prompt)
            import json, re

            # extract JSON safely
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
                feedback = result.get("feedback", "Good attempt!").strip()
                score = int(result.get("score", 0))
            else:
                feedback = "AI could not parse feedback correctly."
                score = 60
        else:
            feedback = f"Good effort! Try providing more details for {user_career} interviews."
            score = 65

        # ✅ Save feedback & update progress
        if db is not None and uid:
            interview_ref = db.reference(f"/users/{uid}/interview_feedback")
            interview_ref.push({
                "career": user_career,
                "question": question,
                "answer": answer,
                "feedback": feedback,
                "score": score
            })

            # Compute new preparedness
            all_feedback = interview_ref.get() or {}
            total = sum([v.get("score", 0) for v in all_feedback.values()])
            avg = round(total / max(len(all_feedback), 1))
            db.reference(f"/users/{uid}/metrics/interview_preparedness").set(avg)

            # 🎯 Update XP & progress based on actual AI score
            user_ref = db.reference(f"/users/{uid}")
            user_data = user_ref.get() or {}

            current_xp = user_data.get("xp", 0)
            current_progress = user_data.get("progress", 0)

            # Dynamic XP — higher score, higher XP
            xp_gain = int(score * 1.5)  # e.g. 90 score = +135 XP
            progress_gain = round(score / 50, 1)  # e.g. 80 score = +1.6%

            new_xp = current_xp + xp_gain
            new_progress = min(current_progress + progress_gain, 100)

            user_ref.update({
                "xp": new_xp,
                "progress": new_progress,
                "quiz_score": score
            })

        return jsonify({
            "feedback": feedback,
            "score": score
        })

    except Exception as e:
        print(f"❌ Feedback Error: {e}")
        return jsonify({"error": "Could not generate feedback"}), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles chat messages for AI Mentor"""
    try:
        data = request.json or {}
        user_prompt = data.get('prompt', '')
        if model:
            chat_prompt = f"""
            You are a friendly AI mentor named CodePath.
            Reply clearly and briefly (max 5 sentences).
            No markdown, no lists — just simple, human-like answers.
            User: {user_prompt}
            """
            response = model.generate_content(chat_prompt)
            reply = response.text.strip()
            reply = reply.replace("**", "").replace("*", "").replace("#", "")
        else:
            reply = "AI backend not available."
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"❌ Chatbot Error: {e}")
        return jsonify({"error": "Failed to generate AI response"}), 500
    # -----------------------
# ---------------- submit quiz result ----------------
@app.route('/api/submit-quiz', methods=['POST'])
def api_submit_quiz():
    """
    Expects JSON: { "username": "<username or uid>", "score": <int>, "stream": "<stream>" }
    Saves quiz and updates xp/quiz_score under user's DB record.
    """
    try:
        data = request.json or {}
        username = data.get('username') or session.get('uid')
        score = int(data.get('score', 0))
        stream = data.get('stream', 'General')

        if not username:
            return jsonify({"error": "username missing"}), 400

        if db is None:
            return jsonify({"error": "db not available"}), 500

        # push quiz
        db.reference(f"users/{username}/quizzes/{stream}").push({"score": score})
        # update summary
        user_ref = db.reference(f"users/{username}")
        cur = user_ref.get() or {}
        new_xp = cur.get("xp", 0) + score * 10
        user_ref.update({"last_quiz_score": score, "xp": new_xp, "quiz_score": score})
        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ submit quiz error: {e}")
        return jsonify({"error": "Failed to save quiz"}), 500


# ---------------- debug route ----------------
@app.route('/debug-current-user')
def debug_current_user():
    uid = session.get('uid') or request.args.get('uid')
    if not uid:
        return "No uid"
    if db is None:
        return "Firebase not available"
    data = db.reference(f"users/{uid}").get()
    return jsonify({"uid": uid, "data": data})
# --------------------------
# --- Save User API (for onboarding) ---
# --------------------------
@app.route('/save_user', methods=['POST'])
def save_user():
    """Saves new onboarding data to Firebase and returns success JSON."""
    try:
        data = request.get_json(force=True)
        name = data.get("name")
        career = data.get("career")
        skill = data.get("skill")

        print("📥 Received user:", data)

        if not name or not career or not skill:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Try to get current user (session)
        uid = session.get('uid') or uid_from_email(name)  # fallback hash by name

        if db is not None:
            ref = db.reference(f"/users/{uid}")
            ref.update({
                "name": name,
                "career": career,
                "skill_level": skill
            })
            print(f"✅ User saved to Firebase: {name}")
        else:
            print("⚠️ Firebase not connected, skipping save.")

        return jsonify({"status": "success", "message": "User saved successfully"})

    except Exception as e:
        print(f"❌ Error saving user: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
# --------------------------------------------------------------------
# 🔹 RESOURCE PROGRESS TRACKING ENDPOINTS
# --------------------------------------------------------------------
# --------------------------------------------------------------------
# 🔹 RESOURCE PROGRESS TRACKING ENDPOINTS (Updated)
# --------------------------------------------------------------------

@app.route('/api/start-resource', methods=['POST'])
def api_start_resource():
    """Start a resource: save progress (40%) for that skill in Firebase"""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({"error": "not_logged_in"}), 401

        data = request.json or {}
        skill = data.get('title')  # Skill name (e.g., DevOps Engineer)
        progress = data.get('progress', 40)

        if not skill:
            return jsonify({"error": "missing_skill"}), 400

        # Store resource data by skill name
        db.reference(f"users/{uid}/resources/{skill}").set({
            "progress": progress,
            "completed": False,
            "timestamp": int(time.time())
        })

        # ⭐ NEW LINE (VERY IMPORTANT)
        recompute_user_overall_progress(uid)

        print(f"✅ {skill} started for user {uid}")
        return jsonify({"ok": True, "message": f"Started {skill}"})
    except Exception as e:
        print("❌ start-resource error:", e)
        return jsonify({"error": "server_error", "message": str(e)}), 500

@app.route('/api/mark-resource-progress', methods=['POST'])
def api_mark_resource_progress():
    """Mark resource as completed (100%) for that skill"""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({"error": "not_logged_in"}), 401

        data = request.json or {}
        skill = data.get('title')
        progress = data.get('progress', 100)

        if not skill:
            return jsonify({"error": "missing_skill"}), 400

        # Update resource completion in Firebase
        db.reference(f"users/{uid}/resources/{skill}").update({
            "progress": progress,
            "completed": True
        })

        # ⭐ NEW LINE (VERY IMPORTANT)
        recompute_user_overall_progress(uid)

        # 🎁 Add XP reward when user completes resource
        user_ref = db.reference(f"users/{uid}")
        cur = user_ref.get() or {}
        new_xp = cur.get("xp", 0) + 150
        user_ref.update({"xp": new_xp})

        print(f"🏁 {skill} marked complete by {uid}, XP: +150")
        return jsonify({"ok": True, "message": f"Completed {skill}"})
    except Exception as e:
        print("❌ mark-resource-progress error:", e)
        return jsonify({"error": "server_error", "message": str(e)}), 500



@app.route('/api/submit-resource-quiz', methods=['POST'])
def api_submit_resource_quiz():
    """Save quiz score for a resource and update XP"""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({"error": "not_logged_in"}), 401
        data = request.json or {}
        resource_id = data.get('resource_id')
        score = int(data.get('score', 0))

        qref = db.reference(f"users/{uid}/resources/{resource_id}/quizzes")
        qref.push({"score": score, "timestamp": int(time.time())})

        user_ref = db.reference(f"users/{uid}")
        cur = user_ref.get() or {}
        new_xp = cur.get("xp", 0) + int(score * 0.5)
        user_ref.update({"xp": new_xp, "last_quiz_score": score})

        return jsonify({"ok": True, "new_xp": new_xp})
    except Exception as e:
        print("❌ submit-resource-quiz error:", e)
        return jsonify({"error": "server_error", "message": str(e)}), 500


@app.route('/api/get-user-resources', methods=['GET'])
def api_get_user_resources():
    """Return all resources for the logged-in user"""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({"error": "not_logged_in"}), 401
        data = db.reference(f"users/{uid}/resources").get() or {}
        return jsonify({"resources": data})
    except Exception as e:
        print("❌ get-user-resources error:", e)
        return jsonify({"error": "server_error", "message": str(e)}), 500
    
@app.route('/api/resources/ai', methods=['POST'])
def api_resources_ai():
    """
    AI search endpoint: expects JSON {"query":"..."} and returns {"html": "<clean html>"}
    """
    try:
        data = request.get_json(force=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"html": "<p>Please type a topic to search.</p>"}), 200

        # Optional: tie to user career for relevance
        uid = session.get('uid')
        user_career = "General"
        if uid and db is not None:
            user_data = db.reference(f"/users/{uid}").get() or {}
            user_career = user_data.get("career", "General")

        if model:
            prompt = f"""
            You are an expert mentor for a {user_career}.
            Find the BEST free learning resources for: "{query}".
            Return clean, minimal HTML only using <h3>, <ul>, <li>, <a>, <p>.
            Sections:
            - 3 YouTube tutorials (title + link + 1-line why)
            - 2 free courses or docs (Coursera/Docs/W3/Kaggle/etc.)
            - 2 tools/libraries (name + 1-line usage)
            - 1 short motivational line
            No markdown. No inline styles. Just semantic HTML.
            """
            resp = model.generate_content(prompt)
            html = resp.text.strip()
        else:
            html = "<p>AI model not available right now.</p>"

        return jsonify({"html": html})
    except Exception as e:
        print("❌ /api/resources/ai error:", e)
        return jsonify({"html": "<p>⚠️ Error fetching AI resources. Try again.</p>"}), 200



# ---------------- Save or Get Resource Progress ----------------
@app.route('/api/resource-progress', methods=['POST', 'GET'])
def api_resource_progress():
    """
    Handles saving and loading user's resource progress.
    POST expects: { "resourceId": "...", "progress": 50 }
    GET returns all saved progress for the logged-in user.
    """
    uid = session.get('uid')
    if not uid:
        return jsonify({"error": "User not logged in"}), 401

    try:
        if request.method == 'POST':
            data = request.json or {}
            resource_id = data.get('resourceId')
            progress = data.get('progress', 0)
            if not resource_id:
                return jsonify({"error": "Missing resourceId"}), 400

            if db is not None:
                db.reference(f"users/{uid}/resources/{resource_id}").set({"progress": progress})
                print(f"✅ Saved progress {progress}% for {resource_id}")
            return jsonify({"ok": True})

        elif request.method == 'GET':
            if db is not None:
                resources = db.reference(f"users/{uid}/resources").get() or {}
                return jsonify(resources)
            else:
                return jsonify({})
    except Exception as e:
        print(f"❌ Resource Progress Error: {e}")
        return jsonify({"error": "Failed to process resource progress"}), 500
        
        
@app.route('/resume-analyzer')
def resume_analyzer():
    return render_template('resume.html')


@app.route('/api/analyze-resume', methods=['POST'])
def analyze_resume():
    """Analyze uploaded resume using AI"""
    try:
        file = request.files.get('resume')

        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        text = file.read().decode('utf-8', errors='ignore')

        # If AI model is available
        if model:
            prompt = f"""
            You are an expert resume reviewer.
            Analyze this resume and give:
            - Overall summary
            - 3 strengths
            - 3 weaknesses
            - ATS score (0–100)
            - Suggestions to improve
            Resume:
            {text}
            Return JSON only:
            {{
              "summary": "...",
              "strengths": ["...","...","..."],
              "weaknesses": ["...","...","..."],
              "ats": 0,
              "suggestions": ["...","..."]
            }}
            """
            response = model.generate_content(prompt)
            import re, json
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            data = json.loads(match.group(0))
        else:
            # Fallback basic analysis
            data = {
                "summary": "Good resume. Improves clarity & structure.",
                "strengths": ["Clear education details", "Good skills", "Readable formatting"],
                "weaknesses": ["Add measurable achievements", "Add projects", "Add internship details"],
                "ats": 65,
                "suggestions": ["Add certifications", "Mention tools used"]
            }

        return jsonify(data)

    except Exception as e:
        print("Resume Analysis Error:", e)
        return jsonify({"error": "Server error"}), 500
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    uid = session.get('uid')
    if not uid:
        return redirect('/login')

    user_ref = db.reference(f"users/{uid}")
    user_data = user_ref.get() or {}

    if request.method == 'POST':
        name = request.form.get('name','')
        career = request.form.get('career','')
        skill = request.form.get('skill','')

        user_ref.update({
            "name": name,
            "career": career,
            "skill_level": skill
        })

        return render_template('profile.html',
                               user=user_data,
                               success="Profile updated!")

    return render_template('profile.html', user=user_data)






# --------------------------
# --- Run App -------------
# --------------------------
if __name__ == '__main__':
    app.run(debug=True)


        