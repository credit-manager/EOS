"""Tests for Ask EOS Engine — intent classification, entity resolution, filter extraction, query building."""

from backend.app.ai.copilot.engine import (
    ENTITY_KEYWORDS,
    IntentClassifier,
    IntentType,
    EntityResolver,
    FilterExtractor,
    QueryBuilder,
)


# ===================================================================
# 1. Intent Classification (query vs analysis vs action)
# ===================================================================

class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_action_intent_create(self):
        intent, confidence = self.classifier.classify("create a new invoice", {})
        assert intent == IntentType.ACTION
        assert confidence >= 0.8

    def test_action_intent_approve(self):
        intent, confidence = self.classifier.classify("approve the purchase order", {})
        assert intent == IntentType.ACTION
        assert confidence >= 0.8

    def test_action_intent_send(self):
        intent, confidence = self.classifier.classify("send the report to the client", {})
        assert intent == IntentType.ACTION

    def test_action_intent_delete(self):
        intent, confidence = self.classifier.classify("delete the old records", {})
        assert intent == IntentType.ACTION

    def test_action_intent_cancel(self):
        intent, confidence = self.classifier.classify("cancel the subscription", {})
        assert intent == IntentType.ACTION

    def test_explanation_intent_why(self):
        intent, confidence = self.classifier.classify("why was this invoice overdue", {})
        assert intent == IntentType.EXPLANATION
        assert confidence >= 0.85

    def test_explanation_intent_explain(self):
        intent, confidence = self.classifier.classify("explain the budget variance", {})
        assert intent == IntentType.EXPLANATION

    def test_comparison_intent_compare(self):
        intent, confidence = self.classifier.classify("compare Q1 vs Q2 revenue", {})
        assert intent == IntentType.COMPARISON
        assert confidence >= 0.8

    def test_comparison_intent_ranking(self):
        intent, confidence = self.classifier.classify("top 5 customers by revenue", {})
        assert intent == IntentType.COMPARISON

    def test_recommendation_intent(self):
        intent, confidence = self.classifier.classify("what needs urgent attention", {})
        assert intent == IntentType.RECOMMENDATION
        assert confidence >= 0.85

    def test_analysis_intent_trend(self):
        intent, confidence = self.classifier.classify("analyze the sales trend", {})
        assert intent == IntentType.ANALYSIS
        assert confidence >= 0.8

    def test_analysis_intent_forecast(self):
        intent, confidence = self.classifier.classify("forecast next quarter revenue", {})
        assert intent == IntentType.ANALYSIS

    def test_summary_intent(self):
        intent, confidence = self.classifier.classify("give me a summary of all projects", {})
        assert intent == IntentType.SUMMARY
        assert confidence >= 0.85

    def test_summary_intent_dashboard(self):
        intent, confidence = self.classifier.classify("show me the dashboard", {})
        assert intent == IntentType.SUMMARY

    def test_default_is_query(self):
        intent, confidence = self.classifier.classify("list all customers", {})
        assert intent == IntentType.QUERY
        assert confidence >= 0.5

    def test_query_simple(self):
        intent, confidence = self.classifier.classify("customer count", {})
        assert intent == IntentType.QUERY

    def test_case_insensitive(self):
        intent1, _ = self.classifier.classify("CREATE an invoice", {})
        intent2, _ = self.classifier.classify("create an invoice", {})
        assert intent1 == intent2 == IntentType.ACTION


# ===================================================================
# 2. Entity Resolution (keywords to entity codes)
# ===================================================================

class TestEntityResolver:
    def setup_method(self):
        self.resolver = EntityResolver()

    def test_resolve_invoices(self):
        entities = self.resolver.resolve("show me all invoices", IntentType.QUERY)
        assert "invoice" in entities

    def test_resolve_payments(self):
        entities = self.resolver.resolve("list recent payments", IntentType.QUERY)
        assert "payment" in entities

    def test_resolve_projects(self):
        entities = self.resolver.resolve("which projects are overdue", IntentType.QUERY)
        assert "project" in entities

    def test_resolve_customers(self):
        entities = self.resolver.resolve("show all customers", IntentType.QUERY)
        assert "customer" in entities

    def test_resolve_suppliers(self):
        entities = self.resolver.resolve("list suppliers", IntentType.QUERY)
        assert "supplier" in entities

    def test_resolve_employees(self):
        entities = self.resolver.resolve("show employees in engineering", IntentType.QUERY)
        assert "employee" in entities

    def test_resolve_contracts(self):
        entities = self.resolver.resolve("which contracts are expiring", IntentType.QUERY)
        assert "contract" in entities

    def test_resolve_orders(self):
        entities = self.resolver.resolve("pending purchase orders", IntentType.QUERY)
        assert "order" in entities

    def test_resolve_accounts(self):
        entities = self.resolver.resolve("trial balance for GL accounts", IntentType.QUERY)
        assert "account" in entities

    def test_resolve_budgets(self):
        entities = self.resolver.resolve("budget utilization report", IntentType.QUERY)
        assert "budget" in entities

    def test_resolve_approvals(self):
        entities = self.resolver.resolve("show pending approvals", IntentType.QUERY)
        assert "approval" in entities

    def test_resolve_journal_entries(self):
        entities = self.resolver.resolve("recent journal entries", IntentType.QUERY)
        assert "journal_entry" in entities

    def test_resolve_multiple_entities(self):
        entities = self.resolver.resolve("invoices and payments for customer Acme", IntentType.QUERY)
        assert "invoice" in entities
        assert "payment" in entities
        assert "customer" in entities

    def test_resolve_bills(self):
        entities = self.resolver.resolve("overdue vendor bills", IntentType.QUERY)
        assert "bill" in entities

    def test_resolve_tasks(self):
        entities = self.resolver.resolve("show open tasks", IntentType.QUERY)
        assert "task" in entities

    def test_unmatched_defaults_for_summary(self):
        entities = self.resolver.resolve("give me everything", IntentType.SUMMARY)
        assert len(entities) > 0

    def test_unmatched_defaults_for_query(self):
        entities = self.resolver.resolve("hello", IntentType.QUERY)
        assert "account" in entities

    def test_keyword_coverage(self):
        expected_keywords = {
            "invoice", "bill", "payment", "project", "supplier", "customer",
            "employee", "order", "contract", "task", "account", "budget",
            "approval", "journal_entry",
        }
        assert expected_keywords == set(ENTITY_KEYWORDS.keys())


# ===================================================================
# 3. Filter Extraction from natural language
# ===================================================================

class TestFilterExtractor:
    def setup_method(self):
        self.extractor = FilterExtractor()

    def test_overdue_filter(self):
        filters = self.extractor.extract("show overdue invoices")
        assert filters.get("status") == "overdue"

    def test_pending_filter(self):
        filters = self.extractor.extract("list pending approvals")
        assert filters.get("status") == "pending"

    def test_draft_filter(self):
        filters = self.extractor.extract("show draft entries")
        assert filters.get("status") == "draft"

    def test_completed_filter(self):
        filters = self.extractor.extract("show completed orders")
        assert filters.get("status") == "completed"

    def test_paid_filter(self):
        filters = self.extractor.extract("show paid invoices")
        assert filters.get("status") == "completed"

    def test_date_range_today(self):
        filters = self.extractor.extract("show today's transactions")
        assert filters.get("date_range") == "today"

    def test_date_range_this_week(self):
        filters = self.extractor.extract("weekly report")
        assert filters.get("date_range") == "this_week"

    def test_date_range_this_month(self):
        filters = self.extractor.extract("monthly summary")
        assert filters.get("date_range") == "this_month"

    def test_date_range_this_quarter(self):
        filters = self.extractor.extract("quarterly analysis")
        assert filters.get("date_range") == "this_quarter"

    def test_date_range_this_year(self):
        filters = self.extractor.extract("yearly revenue")
        assert filters.get("date_range") == "this_year"

    def test_high_value_filter(self):
        filters = self.extractor.extract("show high value invoices")
        assert filters.get("amount_min") == 100000

    def test_low_value_filter(self):
        filters = self.extractor.extract("small payments")
        assert filters.get("amount_max") == 1000

    def test_past_due_filter(self):
        filters = self.extractor.extract("past due bills")
        assert filters.get("status") == "overdue"

    def test_late_filter(self):
        filters = self.extractor.extract("late payments")
        assert filters.get("status") == "overdue"

    def test_expired_filter(self):
        filters = self.extractor.extract("expired contracts")
        assert filters.get("status") == "overdue"

    def test_open_filter(self):
        filters = self.extractor.extract("open orders")
        assert filters.get("status") == "pending"

    def test_waiting_filter(self):
        filters = self.extractor.extract("waiting for approval")
        assert filters.get("status") == "pending"

    def test_no_filters_for_generic(self):
        filters = self.extractor.extract("show me everything")
        assert len(filters) == 0

    def test_multiple_filters(self):
        filters = self.extractor.extract("overdue invoices this month")
        assert filters.get("status") == "overdue"
        assert filters.get("date_range") == "this_month"

    def test_expensive_filter(self):
        filters = self.extractor.extract("expensive purchases")
        assert filters.get("amount_min") == 100000


# ===================================================================
# 4. Query Building
# ===================================================================

class TestQueryBuilder:
    def setup_method(self):
        self.builder = QueryBuilder()

    def test_build_query_for_invoices(self):
        plan = self.builder.build(
            entities=["invoice"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "invoice"
        assert "invoice_number" in plan["fields"]
        assert "total_amount" in plan["fields"]
        assert plan["limit"] == 20

    def test_build_query_for_payments(self):
        plan = self.builder.build(
            entities=["payment"],
            intent=IntentType.QUERY,
            filters={"status": "pending"},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "payment"
        assert plan["filters"]["status"] == "pending"
        assert "amount" in plan["fields"]

    def test_build_query_for_projects(self):
        plan = self.builder.build(
            entities=["project"],
            intent=IntentType.ANALYSIS,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "project"
        assert "budget" in plan["fields"]
        assert "spent" in plan["fields"]

    def test_build_query_for_customers(self):
        plan = self.builder.build(
            entities=["customer"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "customer"
        assert "name" in plan["fields"]
        assert "total_revenue" in plan["fields"]

    def test_build_query_for_employees(self):
        plan = self.builder.build(
            entities=["employee"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "employee"
        assert "department" in plan["fields"]

    def test_build_query_for_suppliers(self):
        plan = self.builder.build(
            entities=["supplier"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "supplier"
        assert "rating" in plan["fields"]

    def test_build_query_for_accounts(self):
        plan = self.builder.build(
            entities=["account"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "account"
        assert "debit" in plan["fields"]
        assert "credit" in plan["fields"]

    def test_build_query_defaults_to_first_entity(self):
        plan = self.builder.build(
            entities=["invoice", "payment"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "invoice"
        assert plan["entities"] == ["invoice", "payment"]

    def test_build_query_empty_entities(self):
        plan = self.builder.build(
            entities=[],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "account"

    def test_build_query_includes_sort(self):
        plan = self.builder.build(
            entities=["invoice"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert "sort" in plan
        assert plan["sort"]["order"] == "desc"

    def test_build_query_for_tasks(self):
        plan = self.builder.build(
            entities=["task"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "task"
        assert "priority" in plan["fields"]

    def test_build_query_for_contracts(self):
        plan = self.builder.build(
            entities=["contract"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "contract"
        assert "value" in plan["fields"]

    def test_build_query_for_approvals(self):
        plan = self.builder.build(
            entities=["approval"],
            intent=IntentType.QUERY,
            filters={},
            tenant_id="test-tenant",
        )
        assert plan["entity"] == "approval"
        assert "status" in plan["fields"]

    def test_build_query_preserves_filters(self):
        plan = self.builder.build(
            entities=["invoice"],
            intent=IntentType.QUERY,
            filters={"status": "overdue", "date_range": "this_month"},
            tenant_id="test-tenant",
        )
        assert plan["filters"]["status"] == "overdue"
        assert plan["filters"]["date_range"] == "this_month"
