from app.core.config import get_settings
from app.deep_research.graph import DeepResearchGraph
from app.deep_research.llm import StructuredDeepResearchAnswerer
from app.providers.llm.openai_compatible import OpenAICompatibleProvider
from app.services.market import get_market_service


def build_runtime_deep_research_graph() -> DeepResearchGraph:
    settings = get_settings()
    answerer = None
    if (
        settings.deepseek_api_key is not None
        and settings.deepseek_api_key.get_secret_value().strip()
    ):
        answerer = StructuredDeepResearchAnswerer(
            OpenAICompatibleProvider(
                settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                timeout_seconds=settings.provider_timeout_seconds * 3,
            )
        )
    return DeepResearchGraph(get_market_service(), answerer=answerer)
