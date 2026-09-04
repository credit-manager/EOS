import pytest

from core.experience_engine.form_engine import FormEngine


def test_arithmetic_formula_is_supported():
    engine = FormEngine()
    assert engine._eval_formula("quantity * unit_price", {"quantity": 4, "unit_price": 12.5}) == 50


def test_formula_cannot_execute_python():
    engine = FormEngine()
    with pytest.raises(ValueError):
        engine._eval_formula("__import__('os').system('echo unsafe')", {})


def test_formula_rejects_attribute_and_call_access():
    engine = FormEngine()
    with pytest.raises(ValueError):
        engine._eval_formula("quantity.real", {"quantity": 4})


def test_formula_rejects_non_numeric_fields():
    engine = FormEngine()
    with pytest.raises(ValueError):
        engine._eval_formula("quantity + name", {"quantity": 4, "name": "x"})


def test_formula_rejects_excessive_exponent():
    engine = FormEngine()
    with pytest.raises(ValueError):
        engine._eval_formula("2 ** 101", {})
