import os
import json
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GovSync AI Voice Assistant", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = AsyncGroq(api_key=GROQ_API_KEY)

class ChatRequest(BaseModel):
    message: str

SYSTEM_INSTRUCTION = """
You are 'GovSync Sahayak', an AI Assistant for Maharashtra Government schemes.

BILINGUAL RULES:
- If citizen asks in Tamil/Tanglish or says "Tamil la sollu":
  Respond STRICTLY in conversational TANGLISH (Tamil in English letters). No Tamil script.
- If citizen asks in English:
  Respond in clear English.

SCHEMES GROUNDING:
1. SKILL_STIPEND_2026: Skill Development Stipend (Income < 1.5L, Age 18-30, Rs 10,000 monthly allowance).
2. FARMER_SOLAR_PUMP_2026: Solar Agriculture Pump Scheme (Marginal farmers, 95% subsidy).
3. HIGHER_EDU_SCHOLARSHIP_2026: Post-Matric Higher Education Scholarship (Family Income < Rs 2.5L, full tuition waiver).

INTENT & ACTION RULES (CRITICAL):
Case 1: User wants to APPLY (e.g. contains 'apply', 'help me apply', 'apply pannu', 'yes', 'ok', 'aama', 'vendum'):
- Set "action": "OPEN_CONSENT_POPUP"
- Set "scheme_id": Matching scheme code (e.g., "FARMER_SOLAR_PUMP_2026")
- Reply: "Sure, opening the one-time consent verification form for you." (or Tanglish: "Kandippa, consent verification form-ah open panren.")

Case 2: User only asks for INFO/EXPLANATION (e.g., 'what schemes available', 'scheme pathi sollu', 'details'):
- Set "action": "NONE"
- Set "scheme_id": null
- Explain briefly in under 20 words and end with: "Would you like to apply?" (or "Apply panringala?")

Output ONLY valid JSON:
{"reply": "response text", "action": "NONE"|"OPEN_CONSENT_POPUP", "scheme_id": "SCHEME_NAME"|null}
"""

def detect_tanglish_demand(text: str) -> bool:
    keywords = ['tamil', 'sollu', 'paththi', 'panni', 'pannu', 'venum', 'epdi', 'soller', 'irukku', 'enna', 'thamil', 'aama']
    return any(k in text.lower() for k in keywords) or bool(re.search(r'[\u0B80-\u0BFF]', text))

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        user_msg = req.message
        is_tanglish = detect_tanglish_demand(user_msg)
        
        # Explicit user-level trigger checking
        apply_keywords = ["apply", "vendum", "venum", "register", "enroll", "aama", "yes", "ok"]
        user_wants_apply = any(w in user_msg.lower() for w in apply_keywords)

        prompt = f"Citizen: {user_msg}\n"
        if user_wants_apply:
            prompt += "INSTRUCTION: Citizen wants to apply. You MUST set action to 'OPEN_CONSENT_POPUP' and provide the matching scheme_id. Respond in JSON:"
        elif is_tanglish:
            prompt += "INSTRUCTION: Respond in Tanglish. Explain and ask 'Apply panringala?'. action is 'NONE'. Respond in JSON:"
        else:
            prompt += "INSTRUCTION: Respond in English. Explain and ask 'Would you like to apply?'. action is 'NONE'. Respond in JSON:"

        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.1,
            max_tokens=300
        )
        
        raw_text = chat_completion.choices[0].message.content.strip()
        raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        json_match = re.search(r'\{[\s\S]*?\}', raw_text)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = {"reply": raw_text, "action": "NONE", "scheme_id": None}

        # Fallback guarantee: User 'apply' ketrunda popup compulsory open aaganum
        action = data.get("action", "NONE")
        scheme_id = data.get("scheme_id", None)
        
        if user_wants_apply and action != "OPEN_CONSENT_POPUP":
            action = "OPEN_CONSENT_POPUP"
            if "solar" in user_msg.lower():
                scheme_id = "FARMER_SOLAR_PUMP_2026"
            elif "stipend" in user_msg.lower():
                scheme_id = "SKILL_STIPEND_2026"
            else:
                scheme_id = "HIGHER_EDU_SCHOLARSHIP_2026"

        return {
            "reply": str(data.get("reply", "Opening consent form...")).strip(),
            "action": action,
            "scheme_id": scheme_id
        }
        
    except Exception as e:
        print("Backend Inference Error:", str(e))
        return {
            "reply": "Kshamikanum, error aayiduchu. Please try again.",
            "action": "NONE",
            "scheme_id": None
        }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)