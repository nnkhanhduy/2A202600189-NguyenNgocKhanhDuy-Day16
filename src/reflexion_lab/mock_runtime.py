from __future__ import annotations
import os
import json
import requests
import time
from dotenv import load_dotenv
from .schemas import QAExample, JudgeResult, ReflectionEntry

load_dotenv() # Nạp biến môi trường từ file .env
from .utils import normalize_answer
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> tuple[str, int]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                # Bị giới hạn Rate Limit, nghỉ một chút rồi thử lại
                time.sleep(5 * (attempt + 1))
                continue
            else:
                raise Exception(f"Groq API Error: {response.text}")
        except (requests.exceptions.RequestException, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            else:
                raise Exception(f"Failed after {max_retries} retries. Final error: {str(e)}")
        
    res_data = response.json()
    content = res_data["choices"][0]["message"]["content"]
    # Lấy token thực tế từ API
    total_tokens = res_data.get("usage", {}).get("total_tokens", 0)
    
    return content, total_tokens

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> tuple[str, int]:
    context_str = "\n\n".join([f"Source: {c.title}\nContent: {c.text}" for c in example.context])
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {example.question}"
    
    if agent_type == "reflexion" and reflection_memory:
        reflections = "\n".join([f"- {r}" for r in reflection_memory])
        user_prompt += f"\n\nPrevious Reflections and Lessons Learned:\n{reflections}\n\nPlease use these lessons to provide a better answer."

    return call_llm(ACTOR_SYSTEM, user_prompt)

def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int]:
    user_prompt = (
        f"Question: {example.question}\n"
        f"Gold Answer: {example.gold_answer}\n"
        f"Agent Answer: {answer}\n\n"
        "Evaluate the Agent Answer against the Gold Answer."
    )
    
    response_json, tokens = call_llm(EVALUATOR_SYSTEM, user_prompt, json_mode=True)
    data = json.loads(response_json)
    
    def sanitize_list(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.lower() in ["none", "n/a", "null", ""]:
            return []
        if val is None:
            return []
        return [str(val)]
        
    result = JudgeResult(
        score=data.get("score", 0),
        reason=data.get("reason", "No reason provided"),
        missing_evidence=sanitize_list(data.get("missing_evidence", [])),
        spurious_claims=sanitize_list(data.get("spurious_claims", []))
    )
    return result, tokens

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult, answer: str) -> tuple[ReflectionEntry, int]:
    user_prompt = (
        f"Question: {example.question}\n"
        f"Previous Answer: {answer}\n"
        f"Feedback from Evaluator: {judge.reason}\n"
        f"Missing Evidence: {', '.join(judge.missing_evidence)}\n"
        "Analyze why the answer was incorrect and suggest a strategy for the next attempt."
    )
    
    reflection_text, tokens = call_llm(REFLECTOR_SYSTEM, user_prompt)
    
    entry = ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=judge.reason,
        lesson=reflection_text,
        next_strategy="Focus on the missing evidence and follow the reflection advice."
    )
    return entry, tokens
