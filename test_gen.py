import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath('crm.py')))

from tracker.db import get_db_connection
from generator.llm_generator import generate_ai_pitch

def main():
    conn = get_db_connection()
    conn.row_factory = dict_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cur = conn.cursor()
    
    # Get a recent vacancy
    cur.execute("SELECT * FROM vacancies ORDER BY id DESC LIMIT 1")
    vacancy = cur.fetchone()
    
    if not vacancy:
        print("No vacancies found.")
        return
        
    print(f"Testing generation for: {vacancy.get('title')} at {vacancy.get('company')}\n")
    print("Generating...\n")
    
    # Run generation
    # Profile can be a mock dict
    profile = {
        "name": "Егор",
        "role": "Frontend / Fullstack Engineer",
        "experience": "5+ лет продуктовой разработки, Next.js, React, Docker, CI/CD",
        "keywords": "React, Next.js, Node.js, TypeScript",
        "contacts_structured": {
            "telegram": "@egor",
            "email": "egor@test.com",
            "github": "github.com/egor",
            "linkedin": "linkedin.com/in/egor"
        }
    }
    
    try:
        result = generate_ai_pitch(vacancy, profile, lang="ru")
        print("=== COVER LETTER ===")
        print(result.get("cover_letter", "Error generating cover letter"))
        print("\n=== SHORT DM ===")
        print(result.get("short_dm", "Error generating short DM"))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    main()
