"""
ReasoningEngine — Chain-of-Thought, Tree-of-Thought, ReAct, Reflection, Self-Critique
The most advanced reasoning system available (2026).
"""
import asyncio, json, logging, re
from typing import Any, Optional

log = logging.getLogger("ReasoningEngine")

class ReasoningEngine:
    """Multi-strategy reasoning: CoT, ToT, ReAct, Reflection, Meta-Reasoning"""

    STRATEGIES = ["cot", "tot", "react", "reflection", "self_critique", "meta"]

    def __init__(self, router, memory, default_strategy="auto"):
        self.router = router
        self.memory = memory
        self.default_strategy = default_strategy
        self.trace_log = []

    async def think(self, problem: str, strategy: str = "auto", depth: int = 3) -> dict:
        if strategy == "auto":
            strategy = await self._select_strategy(problem)
        log.info(f"Reasoning [{strategy}] on: {problem[:80]}...")
        
        methods = {
            "cot": self._chain_of_thought,
            "tot": self._tree_of_thought,
            "react": self._react,
            "reflection": self._reflection,
            "self_critique": self._self_critique,
            "meta": self._meta_reasoning,
        }
        
        fn = methods.get(strategy, self._chain_of_thought)
        result = await fn(problem, depth)
        self.trace_log.append({"problem": problem, "strategy": strategy, "result": result})
        
        if self.memory and hasattr(self.memory, "store"):
            try:
                await self.memory.store(f"reasoning:{problem[:50]}", result)
            except Exception:
                pass
        return result

    async def _select_strategy(self, problem: str) -> str:
        prompt = f"""Given this problem, select the BEST reasoning strategy.
Problem: {problem}
Strategies:
- cot: step-by-step linear reasoning (best for math, logic)
- tot: tree of possibilities (best for creative or multi-path problems)
- react: reason+act cycles with tool use (best for research/OSINT)
- reflection: reflect and improve own answer iteratively
- self_critique: generate answer then critique it
- meta: reason about which strategy to use recursively
Reply with ONLY the strategy name."""
        try:
            resp = await self.router.complete(prompt, max_tokens=20, temperature=0.1)
            s = resp.strip().lower().split()[0]
            return s if s in self.STRATEGIES else "cot"
        except Exception:
            return "cot"

    async def _chain_of_thought(self, problem: str, depth: int = 3) -> dict:
        prompt = f"""Solve this step by step. Show ALL reasoning.
Problem: {problem}

Think through this carefully:
Step 1: Understand what is being asked
Step 2: Break down the problem
Step 3: Reason through each component
Step 4: Synthesize the answer
Step 5: Verify and finalize

Answer:"""
        answer = await self.router.complete(prompt, max_tokens=1500)
        return {"strategy": "cot", "reasoning": answer, "answer": self._extract_answer(answer)}

    async def _tree_of_thought(self, problem: str, depth: int = 3) -> dict:
        branches = []
        for i in range(3):
            prompt = f"""Explore ONE possible approach to this problem (approach #{i+1}).
Problem: {problem}
Generate a unique solution path and evaluate it. Be creative but rigorous."""
            try:
                branch = await self.router.complete(prompt, max_tokens=600, temperature=0.7)
                branches.append(branch)
            except Exception as e:
                branches.append(f"Branch {i+1} failed: {e}")

        synthesis_prompt = f"""Given these 3 different approaches to: {problem}

Approach 1: {branches[0][:400]}
Approach 2: {branches[1][:400]}  
Approach 3: {branches[2][:400]}

Synthesize the BEST answer combining insights from all approaches:"""
        synthesis = await self.router.complete(synthesis_prompt, max_tokens=800)
        return {"strategy": "tot", "branches": branches, "synthesis": synthesis, "answer": synthesis}

    async def _react(self, problem: str, depth: int = 5) -> dict:
        trace = []
        context = problem
        for step in range(depth):
            prompt = f"""You are a ReAct agent. Given the context, decide: Thought, Action, or Final Answer.
Context: {context}
Step {step+1}/{depth}

Format:
Thought: [your reasoning]
Action: [SEARCH/CALCULATE/ANALYZE/DONE]
Input: [action input]"""
            response = await self.router.complete(prompt, max_tokens=400)
            trace.append(response)
            if "DONE" in response or "Final Answer" in response:
                break
            context += f"\nStep {step+1}: {response}"
        return {"strategy": "react", "trace": trace, "answer": trace[-1]}

    async def _reflection(self, problem: str, depth: int = 3) -> dict:
        initial_prompt = f"Answer this question: {problem}"
        answer = await self.router.complete(initial_prompt, max_tokens=600)
        
        for i in range(depth):
            reflection_prompt = f"""Reflect on and improve this answer.
Problem: {problem}
Current answer: {answer}

Identify weaknesses, gaps, or errors. Provide an improved answer:"""
            answer = await self.router.complete(reflection_prompt, max_tokens=700)
        
        return {"strategy": "reflection", "final_answer": answer, "answer": answer}

    async def _self_critique(self, problem: str, depth: int = 2) -> dict:
        answer = await self.router.complete(f"Answer: {problem}", max_tokens=600)
        
        critique_prompt = f"""Critically evaluate this answer for the problem.
Problem: {problem}
Answer: {answer}

Rate (1-10) and identify: accuracy, completeness, logic errors, missing context.
Then provide an improved version:"""
        critique = await self.router.complete(critique_prompt, max_tokens=800)
        return {"strategy": "self_critique", "original": answer, "critique": critique, "answer": critique}

    async def _meta_reasoning(self, problem: str, depth: int = 3) -> dict:
        meta_prompt = f"""You are a meta-reasoner. First, reason about HOW to reason about this problem.
Problem: {problem}

1. What type of problem is this? (logical/creative/factual/mathematical/ethical)
2. What cognitive strategies are most effective?
3. What biases or pitfalls to avoid?
4. Apply the optimal strategy:"""
        meta = await self.router.complete(meta_prompt, max_tokens=1000)
        return {"strategy": "meta", "meta_analysis": meta, "answer": meta}

    def _extract_answer(self, text: str) -> str:
        patterns = [
            r"(?:Final Answer|Answer|Conclusion|Result):\s*(.+?)(?:\n|$)",
            r"(?:Therefore|Thus|So),\s*(.+?)(?:\n|$)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        return lines[-1] if lines else text[:200]
