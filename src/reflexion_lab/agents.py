from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .mock_runtime import actor_answer, evaluator, reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    def run(self, example: QAExample) -> RunRecord:
        import time
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        
        for attempt_id in range(1, self.max_attempts + 1):
            start_time = time.perf_counter()
            total_attempt_tokens = 0
            
            # 1. Actor generate answer
            answer, actor_tokens = actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            total_attempt_tokens += actor_tokens
            
            # 2. Evaluator judge the answer
            judge, eval_tokens = evaluator(example, answer)
            total_attempt_tokens += eval_tokens
            
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)
            
            current_reflection = None
            final_answer = answer
            final_score = judge.score
            
            # 3. If wrong and reflexion enabled, call Reflector
            if judge.score == 0 and self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                ref_start = time.perf_counter()
                entry, ref_tokens = reflector(example, attempt_id, judge, answer)
                ref_end = time.perf_counter()
                
                total_attempt_tokens += ref_tokens
                latency_ms += int((ref_end - ref_start) * 1000)
                current_reflection = entry
                reflections.append(entry)
                reflection_memory.append(entry.lesson)
            
            trace = AttemptTrace(
                attempt_id=attempt_id, 
                answer=answer, 
                score=judge.score, 
                reason=judge.reason, 
                reflection=current_reflection,
                token_estimate=total_attempt_tokens, # Now it's actual token usage
                latency_ms=latency_ms
            )
            traces.append(trace)
            
            if judge.score == 1:
                break
                
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        
        # Mapping failure modes based on common patterns if failed
        failure_mode = "none" if final_score == 1 else "wrong_final_answer"
        
        return RunRecord(
            qid=example.qid, 
            question=example.question, 
            gold_answer=example.gold_answer, 
            agent_type=self.agent_type, 
            predicted_answer=final_answer, 
            is_correct=bool(final_score), 
            attempts=len(traces), 
            token_estimate=total_tokens, 
            latency_ms=total_latency, 
            failure_mode=failure_mode, 
            reflections=reflections, 
            traces=traces
        )

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
