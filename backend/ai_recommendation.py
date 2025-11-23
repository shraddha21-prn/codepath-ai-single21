# backend/ai_recommendation.py
import json, re, google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

def extract_json(text):
    """Extract first JSON-like object from AI response text."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(match.group(0)) if match else None

def generate_roadmap(career_path, skill_level):
    prompt = f"""
    Generate a detailed, 8-week learning roadmap for an aspiring {career_path} with a {skill_level} skill level.
    Return ONLY a JSON object: {{"roadmap": [{{"week": "Weeks 1-2", "topics": "Topic A, Topic B"}}]}}
    """
    safety = {'HATE':'BLOCK_NONE','HARASSMENT':'BLOCK_NONE','SEXUAL':'BLOCK_NONE','DANGEROUS':'BLOCK_NONE'}
    response = model.generate_content(prompt, safety_settings=safety)
    data = extract_json(response.text)
    return data or {"roadmap":[]}

def generate_quiz(topic):
    prompt = f"""
    Create a 3-question multiple-choice quiz on "{topic}".
    JSON only: {{"quiz":[{{"question":"Q?","options":["A","B","C"],"answer":"A"}}]}}
    """
    safety = {'HATE':'BLOCK_NONE','HARASSMENT':'BLOCK_NONE'}
    response = model.generate_content(prompt, safety_settings=safety)
    data = extract_json(response.text)
    return data or {"quiz":[]}

def get_interview_question():
    prompt = "Generate one technical interview question on data structures or algorithms."
    response = model.generate_content(prompt)
    return response.text.strip()

def get_interview_feedback(question, answer):
    prompt = f"""You are a technical interviewer. Q: "{question}" A: "{answer}" 
    Give concise constructive feedback in one paragraph."""
    response = model.generate_content(prompt)
    return response.text.strip()
