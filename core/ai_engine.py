import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


class AIEngine:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ models
    def create_model(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        model_type: str,
        target_entity: str,
        **kw,
    ) -> str:
        mid = str(uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_ai_models "
                "(id,tenant_id,company_id,name,model_type,target_entity,config,status,"
                "accuracy_score,trained_at,created_at) "
                "VALUES (:id,:tenant_id,:company_id,:name,:model_type,:target_entity,"
                ":config,:status,:accuracy_score,:trained_at,now())"
            ),
            {
                "id": mid,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "name": name,
                "model_type": model_type,
                "target_entity": target_entity,
                "config": json.dumps(kw.get("config")) if kw.get("config") is not None else None,
                "status": kw.get("status", "ready"),
                "accuracy_score": kw.get("accuracy_score"),
                "trained_at": kw.get("trained_at"),
            },
        )
        self.db.commit()
        return mid

    def list_models(
        self, company_id: str, tenant_id: str | None = None, model_type: str | None = None
    ) -> list[dict]:
        sql = "SELECT * FROM dbp_ai_models WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if model_type:
            sql += " AND model_type=:mt"
            params["mt"] = model_type
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    def get_model(self, model_id: str, tenant_id: str) -> dict | None:
        row = self.db.execute(
            text("SELECT * FROM dbp_ai_models WHERE id=:id AND tenant_id=:tenant_id"), {"id": model_id, "tenant_id": tenant_id}
        ).mappings().first()
        return self._serialize(row) if row else None

    def update_model(self, model_id: str, tenant_id: str, **kw) -> dict:
        sets, params = [], {"id": model_id, "tenant_id": tenant_id}
        for field in ("name", "model_type", "target_entity", "status", "accuracy_score", "trained_at"):
            if field in kw:
                sets.append(f"{field}=:{field}")
                params[field] = kw[field]
        if "config" in kw:
            sets.append("config=:config")
            params["config"] = json.dumps(kw["config"]) if kw["config"] is not None else None
        if sets:
            self.db.execute(
                text(f"UPDATE dbp_ai_models SET {','.join(sets)} WHERE id=:id AND tenant_id=:tenant_id"), params
            )
            self.db.commit()
        return self.get_model(model_id, tenant_id)

    # ------------------------------------------------------------------ predictions
    def create_prediction(
        self,
        tenant_id: str,
        company_id: str,
        model_id: str,
        prediction_type: str,
        predicted_value,
        **kw,
    ) -> str:
        pid = str(uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_ai_predictions "
                "(id,tenant_id,company_id,model_id,entity_type,entity_id,prediction_type,"
                "predicted_value,confidence,status,expires_at,created_at) "
                "VALUES (:id,:tenant_id,:company_id,:model_id,:entity_type,:entity_id,"
                ":prediction_type,:predicted_value,:confidence,:status,:expires_at,now())"
            ),
            {
                "id": pid,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "model_id": model_id,
                "entity_type": kw.get("entity_type"),
                "entity_id": kw.get("entity_id"),
                "prediction_type": prediction_type,
                "predicted_value": json.dumps(predicted_value) if not isinstance(predicted_value, str) else predicted_value,
                "confidence": kw.get("confidence"),
                "status": kw.get("status", "pending"),
                "expires_at": kw.get("expires_at"),
            },
        )
        self.db.commit()
        return pid

    def get_prediction(self, prediction_id: str, tenant_id: str) -> dict | None:
        row = self.db.execute(
            text("SELECT * FROM dbp_ai_predictions WHERE id=:id AND tenant_id=:tenant_id"), {"id": prediction_id, "tenant_id": tenant_id}
        ).mappings().first()
        return self._serialize(row) if row else None

    def list_predictions(
        self,
        company_id: str,
        tenant_id: str | None = None,
        model_id: str | None = None,
        entity_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM dbp_ai_predictions WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if model_id:
            sql += " AND model_id=:mid"
            params["mid"] = model_id
        if entity_type:
            sql += " AND entity_type=:et"
            params["et"] = entity_type
        if status:
            sql += " AND status=:st"
            params["st"] = status
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    def acknowledge_prediction(self, prediction_id: str, actual_value, tenant_id: str) -> dict:
        self.db.execute(
            text(
                "UPDATE dbp_ai_predictions SET actual_value=:av, status='verified' WHERE id=:id AND tenant_id=:tenant_id"
            ),
            {
                "av": json.dumps(actual_value) if not isinstance(actual_value, str) else actual_value,
                "id": prediction_id,
                "tenant_id": tenant_id,
            },
        )
        self.db.commit()
        return self.get_prediction(prediction_id, tenant_id)

    # ------------------------------------------------------------------ recommendations
    def create_recommendation(
        self,
        tenant_id: str,
        company_id: str,
        recommendation_type: str,
        title: str,
        description: str,
        **kw,
    ) -> str:
        rid = str(uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_ai_recommendations "
                "(id,tenant_id,company_id,entity_type,entity_id,recommendation_type,"
                "title,description,priority,impact_score,status,created_at) "
                "VALUES (:id,:tenant_id,:company_id,:entity_type,:entity_id,"
                ":recommendation_type,:title,:description,:priority,:impact_score,"
                "'pending',now())"
            ),
            {
                "id": rid,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "entity_type": kw.get("entity_type"),
                "entity_id": kw.get("entity_id"),
                "recommendation_type": recommendation_type,
                "title": title,
                "description": description,
                "priority": kw.get("priority", "medium"),
                "impact_score": kw.get("impact_score"),
            },
        )
        self.db.commit()
        return rid

    def list_recommendations(
        self, company_id: str, tenant_id: str | None = None, status: str | None = None, priority: str | None = None
    ) -> list[dict]:
        sql = "SELECT * FROM dbp_ai_recommendations WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if status:
            sql += " AND status=:st"
            params["st"] = status
        if priority:
            sql += " AND priority=:pr"
            params["pr"] = priority
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    def acknowledge_recommendation(self, rec_id: str, acknowledged_by: str, tenant_id: str) -> dict:
        self.db.execute(
            text(
                "UPDATE dbp_ai_recommendations SET status='acknowledged', "
                "acknowledged_by=:ab, acknowledged_at=now() WHERE id=:id AND tenant_id=:tenant_id"
            ),
            {"ab": acknowledged_by, "id": rec_id, "tenant_id": tenant_id},
        )
        self.db.commit()
        return self._get_recommendation(rec_id, tenant_id)

    def _get_recommendation(self, rec_id: str, tenant_id: str) -> dict | None:
        row = self.db.execute(
            text("SELECT * FROM dbp_ai_recommendations WHERE id=:id AND tenant_id=:tenant_id"), {"id": rec_id, "tenant_id": tenant_id}
        ).mappings().first()
        return self._serialize(row) if row else None

    # ------------------------------------------------------------------ anomalies
    def create_anomaly(
        self,
        tenant_id: str,
        company_id: str,
        entity_type: str,
        metric_name: str,
        expected_value,
        actual_value,
        **kw,
    ) -> str:
        aid = str(uuid4())
        exp = float(expected_value)
        act = float(actual_value)
        if exp != 0:
            deviation = ((act - exp) / exp) * 100
        else:
            deviation = 0.0
        self.db.execute(
            text(
                "INSERT INTO dbp_ai_anomalies "
                "(id,tenant_id,company_id,entity_type,entity_id,metric_name,"
                "expected_value,actual_value,deviation_pct,severity,status,created_at) "
                "VALUES (:id,:tenant_id,:company_id,:entity_type,:entity_id,:metric_name,"
                ":expected_value,:actual_value,:deviation_pct,:severity,'detected',now())"
            ),
            {
                "id": aid,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "entity_type": entity_type,
                "entity_id": kw.get("entity_id"),
                "metric_name": metric_name,
                "expected_value": exp,
                "actual_value": act,
                "deviation_pct": round(deviation, 2),
                "severity": kw.get("severity", "medium"),
            },
        )
        self.db.commit()
        return aid

    def list_anomalies(
        self, company_id: str, tenant_id: str | None = None, status: str | None = None, severity: str | None = None
    ) -> list[dict]:
        sql = "SELECT * FROM dbp_ai_anomalies WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        if tenant_id:
            sql += " AND tenant_id=:tid"
            params["tid"] = tenant_id
        if status:
            sql += " AND status=:st"
            params["st"] = status
        if severity:
            sql += " AND severity=:sv"
            params["sv"] = severity
        rows = self.db.execute(text(sql), params).mappings().all()
        return [self._serialize(r) for r in rows]

    def resolve_anomaly(self, anomaly_id: str, resolved_by: str, tenant_id: str) -> dict:
        self.db.execute(
            text(
                "UPDATE dbp_ai_anomalies SET status='resolved', "
                "resolved_by=:rb, resolved_at=now() WHERE id=:id AND tenant_id=:tenant_id"
            ),
            {"rb": resolved_by, "id": anomaly_id, "tenant_id": tenant_id},
        )
        self.db.commit()
        return self._get_anomaly(anomaly_id, tenant_id)

    def _get_anomaly(self, anomaly_id: str, tenant_id: str) -> dict | None:
        row = self.db.execute(
            text("SELECT * FROM dbp_ai_anomalies WHERE id=:id AND tenant_id=:tenant_id"), {"id": anomaly_id, "tenant_id": tenant_id}
        ).mappings().first()
        return self._serialize(row) if row else None

    # ------------------------------------------------------------------ insights
    def get_insights(self, company_id: str, tenant_id: str | None = None) -> dict:
        base = " WHERE company_id=:cid"
        params: dict = {"cid": company_id}
        tid_filter = ""
        if tenant_id:
            tid_filter = " AND tenant_id=:tid"
            params["tid"] = tenant_id

        model_count = self.db.execute(
            text(f"SELECT COUNT(*) FROM dbp_ai_models{base}{tid_filter}"), params
        ).scalar() or 0

        pending_preds = self.db.execute(
            text(f"SELECT COUNT(*) FROM dbp_ai_predictions{base}{tid_filter} AND status='pending'"), params
        ).scalar() or 0

        active_anomalies = self.db.execute(
            text(f"SELECT COUNT(*) FROM dbp_ai_anomalies{base}{tid_filter} AND status='detected'"), params
        ).scalar() or 0

        open_recs = self.db.execute(
            text(f"SELECT COUNT(*) FROM dbp_ai_recommendations{base}{tid_filter} AND status='pending'"), params
        ).scalar() or 0

        return {
            "model_count": model_count,
            "pending_predictions": pending_preds,
            "active_anomalies": active_anomalies,
            "open_recommendations": open_recs,
        }

    # ------------------------------------------------------------------ helpers
    def _serialize(self, row) -> dict:
        d = dict(row)
        for k, v in d.items():
            if isinstance(v, str) and k in (
                "config", "predicted_value", "actual_value",
            ):
                try:
                    d[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    pass
        if "created_at" in d and d["created_at"] is not None:
            d["created_at"] = str(d["created_at"])
        if "trained_at" in d and d["trained_at"] is not None:
            d["trained_at"] = str(d["trained_at"])
        if "expires_at" in d and d["expires_at"] is not None:
            d["expires_at"] = str(d["expires_at"])
        if "acknowledged_at" in d and d["acknowledged_at"] is not None:
            d["acknowledged_at"] = str(d["acknowledged_at"])
        if "resolved_at" in d and d["resolved_at"] is not None:
            d["resolved_at"] = str(d["resolved_at"])
        return d
