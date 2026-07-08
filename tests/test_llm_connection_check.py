import scripts.check_llm_connection as check_llm_connection


def test_check_config_reports_missing_api_key(monkeypatch):
    monkeypatch.setattr(
        check_llm_connection,
        "get_base_llm_metadata",
        lambda: {
            "provider": "volcengine_ark",
            "model": "deepseek-v4-flash",
            "runtime_model": "deepseek-v4-flash",
            "endpoint_id_configured": False,
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "temperature": 0.2,
            "timeout": 60,
            "api_key_configured": False,
        },
    )

    result = check_llm_connection.check_config()

    assert result["status"] == "failed"
    assert result["checks"]["model_is_deepseek_v4_flash"] is True
    assert result["checks"]["api_key_configured"] is False


def test_check_config_passes_when_deepseek_flash_is_configured(monkeypatch):
    monkeypatch.setattr(
        check_llm_connection,
        "get_base_llm_metadata",
        lambda: {
            "provider": "volcengine_ark",
            "model": "deepseek-v4-flash",
            "runtime_model": "ep-test-endpoint",
            "endpoint_id_configured": True,
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "temperature": 0.2,
            "timeout": 60,
            "api_key_configured": True,
        },
    )

    result = check_llm_connection.check_config()

    assert result["status"] == "ok"
    assert result["checks"]["model_is_deepseek_v4_flash"] is True
    assert result["checks"]["runtime_model_configured"] is True
    assert result["checks"]["endpoint_id_configured"] is True
    assert result["checks"]["api_key_configured"] is True


def test_live_check_explains_invalid_endpoint_or_model(monkeypatch):
    monkeypatch.setattr(
        check_llm_connection,
        "get_base_llm_metadata",
        lambda: {
            "provider": "volcengine_ark",
            "model": "deepseek-v4-flash",
            "runtime_model": "deepseek-v4-flash",
            "endpoint_id_configured": False,
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "temperature": 0.2,
            "timeout": 60,
            "api_key_configured": True,
        },
    )

    class BrokenLLM:
        def invoke(self, prompt):
            raise RuntimeError("InvalidEndpointOrModel.NotFound")

    monkeypatch.setattr(check_llm_connection, "get_base_llm", lambda: BrokenLLM())

    result = check_llm_connection.check_live()

    assert result["status"] == "failed"
    assert result["live_check"]["status"] == "failed"
    assert "MAF_LLM_ENDPOINT_ID" in result["live_check"]["fix"]
