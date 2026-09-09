from pathlib import Path


def test_production_startup_uses_persistent_rs256_configuration():
    main_source = Path("main.py").read_text(encoding="utf-8")
    assert "EOS_JWT_PRIVATE_KEY" not in main_source or "validate_production_config" in main_source
    assert "EOS_SECRET_KEY required in production mode" not in main_source
    assert "Consider RS256 for production" not in main_source


def test_production_auth_has_no_legacy_secret_key_dependency():
    auth_source = Path("core/production_auth.py").read_text(encoding="utf-8")
    adapter_source = Path("core/auth_adapter.py").read_text(encoding="utf-8")
    assert "EOS_SECRET_KEY" not in auth_source
    assert "_get_secret_key" not in adapter_source
    assert 'algorithms=[_get_algorithm()]' in auth_source
    assert 'algorithm=\"RS256\"' in auth_source


def test_production_config_requires_persistent_key_pair():
    config_source = Path("core/production_config.py").read_text(encoding="utf-8")
    assert 'check("EOS_JWT_PRIVATE_KEY"' in config_source
    assert 'check("EOS_JWT_PUBLIC_KEY"' in config_source
    assert 'check("EOS_ALGORITHM"' in config_source
    assert 'r"^RS256$"' in config_source
