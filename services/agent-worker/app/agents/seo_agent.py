import logging
from app.agents.state import SeoAgentState

logger = logging.getLogger(__name__)

class SeoAgent:
    async def retrieve_context(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def generate_seo(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def generate_image(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def finalize(self, state: SeoAgentState) -> SeoAgentState:
        return state
