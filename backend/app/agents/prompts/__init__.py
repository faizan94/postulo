"""System prompts, one module per agent (pattern from mathcrypto/ai-agent-orchestrator).

Each prompt follows the same layout: Scope -> Hard rules -> Return value.
Edit prompts here; the agent modules only import them.
"""

from app.agents.prompts.profile import PROFILE_SYSTEM_PROMPT
from app.agents.prompts.score import SCORE_SYSTEM_PROMPT

__all__ = ["PROFILE_SYSTEM_PROMPT", "SCORE_SYSTEM_PROMPT"]
