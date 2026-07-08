from multiple_agent_finance.llm.base import get_base_llm_metadata


def test_base_llm_metadata_uses_volcengine_deepseek_without_secret():
    metadata = get_base_llm_metadata()

    assert metadata["provider"] == "volcengine_ark"
    assert metadata["model"] == "deepseek-v4-flash"
    assert metadata["runtime_model"]
    assert "endpoint_id_configured" in metadata
    assert metadata["base_url"] == "https://ark.cn-beijing.volces.com/api/v3"
    assert "api_key" not in metadata
