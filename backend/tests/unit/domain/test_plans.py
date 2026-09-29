"""Unit-тесты каталога тарифов."""

from app.domain.plans import (
    DEFAULT_PLAN,
    PLAN_LIMITS,
    get_plan_limits,
    is_valid_plan,
    list_plans_catalog,
)


class TestPlans:
    def test_default_is_free(self):
        assert DEFAULT_PLAN == "free"

    def test_free_limits(self):
        limits = get_plan_limits("free")
        assert limits.max_properties == 3
        assert limits.max_users == 2
        assert limits.max_storage_bytes == 100 * 1024 * 1024

    def test_pro_and_enterprise(self):
        pro = get_plan_limits("pro")
        assert pro.max_properties == 25
        assert pro.max_users == 5
        ent = get_plan_limits("enterprise")
        assert ent.max_properties == 200
        assert ent.max_storage_bytes == 50 * 1024 * 1024 * 1024

    def test_unknown_falls_back_to_free(self):
        assert get_plan_limits("unknown") == PLAN_LIMITS["free"]

    def test_is_valid_plan(self):
        assert is_valid_plan("free")
        assert is_valid_plan("pro")
        assert is_valid_plan("enterprise")
        assert not is_valid_plan("gold")

    def test_catalog_has_three(self):
        catalog = list_plans_catalog()
        assert len(catalog) == 3
        assert [c["id"] for c in catalog] == ["free", "pro", "enterprise"]
        assert catalog[0]["price_rub_monthly"] is None
        assert catalog[1]["price_rub_monthly"] == 990
        assert catalog[2]["price_rub_monthly"] is None
