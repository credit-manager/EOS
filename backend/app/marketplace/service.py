"""Marketplace foundation service."""
from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    MarketplaceApp,
    MarketplaceAuthor,
    MarketplaceCategory,
    MarketplaceInstallation,
    MarketplaceOrder,
    MarketplaceReview,
)


class MarketplaceService:
    def __init__(self, db: Session):
        self.db = db

    # Apps

    def create_app(self, data: dict) -> MarketplaceApp:
        app = MarketplaceApp(**data)
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def get_app(self, app_id: str) -> MarketplaceApp | None:
        return self.db.query(MarketplaceApp).filter(MarketplaceApp.id == app_id).first()

    def get_app_by_code(self, code: str) -> MarketplaceApp | None:
        return self.db.query(MarketplaceApp).filter(MarketplaceApp.code == code).first()

    def list_apps(
        self,
        category: str | None = None,
        pricing_model: str | None = None,
        is_featured: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MarketplaceApp], int]:
        q = self.db.query(MarketplaceApp).filter(MarketplaceApp.is_published)
        if category:
            q = q.filter(MarketplaceApp.category == category)
        if pricing_model:
            q = q.filter(MarketplaceApp.pricing_model == pricing_model)
        if is_featured is not None:
            q = q.filter(MarketplaceApp.is_featured == is_featured)
        if search:
            q = q.filter(
                (MarketplaceApp.name.ilike(f"%{search}%"))
                | (MarketplaceApp.description.ilike(f"%{search}%"))
            )
        total = q.count()
        apps = q.order_by(MarketplaceApp.rating.desc().nullslast(), MarketplaceApp.install_count.desc()).offset(offset).limit(limit).all()
        return apps, total

    def publish_app(self, app_id: str) -> MarketplaceApp | None:
        app = self.get_app(app_id)
        if not app:
            return None
        app.is_published = True
        app.published_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(app)
        return app

    def increment_install(self, app_id: str) -> MarketplaceApp | None:
        app = self.get_app(app_id)
        if not app:
            return None
        app.install_count += 1
        self.db.commit()
        return app

    # Categories

    def create_category(self, data: dict) -> MarketplaceCategory:
        cat = MarketplaceCategory(**data)
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def list_categories(self) -> list[MarketplaceCategory]:
        return self.db.query(MarketplaceCategory).filter(MarketplaceCategory.is_active).order_by(MarketplaceCategory.sort_order).all()

    # Reviews

    def create_review(self, tenant_id: str, user_id: str, data: dict) -> MarketplaceReview:
        review = MarketplaceReview(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        self._update_app_rating(data["app_id"])
        return review

    def list_reviews(self, app_id: str, limit: int = 50) -> list[MarketplaceReview]:
        return self.db.query(MarketplaceReview).filter(MarketplaceReview.app_id == app_id, MarketplaceReview.is_active).order_by(MarketplaceReview.created_at.desc()).limit(limit).all()

    def _update_app_rating(self, app_id: str) -> None:
        from sqlalchemy import func
        result = self.db.query(func.avg(MarketplaceReview.rating), func.count(MarketplaceReview.id)).filter(MarketplaceReview.app_id == app_id, MarketplaceReview.is_active).first()
        app = self.get_app(app_id)
        if app and result[0] is not None:
            app.rating = round(float(result[0]), 2)
            app.rating_count = result[1]
            self.db.commit()

    # Installations

    def install_app(self, app_id: str, tenant_id: str, user_id: str, version: str) -> MarketplaceInstallation:
        installation = MarketplaceInstallation(
            app_id=app_id,
            tenant_id=tenant_id,
            user_id=user_id,
            version=version,
            status="active",
        )
        self.db.add(installation)
        self.db.commit()
        self.db.refresh(installation)
        self.increment_install(app_id)
        return installation

    def list_installations(self, tenant_id: str) -> list[MarketplaceInstallation]:
        return self.db.query(MarketplaceInstallation).filter(MarketplaceInstallation.tenant_id == tenant_id).order_by(MarketplaceInstallation.installed_at.desc()).all()

    # Orders

    def create_order(self, tenant_id: str, user_id: str, data: dict) -> MarketplaceOrder:
        order = MarketplaceOrder(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def list_orders(self, tenant_id: str, limit: int = 50) -> list[MarketplaceOrder]:
        return self.db.query(MarketplaceOrder).filter(MarketplaceOrder.tenant_id == tenant_id).order_by(MarketplaceOrder.created_at.desc()).limit(limit).all()

    # Authors

    def create_author(self, user_id: str, data: dict) -> MarketplaceAuthor:
        author = MarketplaceAuthor(user_id=user_id, **data)
        self.db.add(author)
        self.db.commit()
        self.db.refresh(author)
        return author

    def get_author(self, author_id: str) -> MarketplaceAuthor | None:
        return self.db.query(MarketplaceAuthor).filter(MarketplaceAuthor.id == author_id).first()

    def get_author_by_user(self, user_id: str) -> MarketplaceAuthor | None:
        return self.db.query(MarketplaceAuthor).filter(MarketplaceAuthor.user_id == user_id).first()

    def list_authors(self, limit: int = 50) -> list[MarketplaceAuthor]:
        return self.db.query(MarketplaceAuthor).order_by(MarketplaceAuthor.total_installs.desc()).limit(limit).all()

    # Stats

    def get_stats(self) -> dict:
        total_apps = self.db.query(MarketplaceApp).filter(MarketplaceApp.is_published).count()
        total_categories = self.db.query(MarketplaceCategory).filter(MarketplaceCategory.is_active).count()
        total_installs = self.db.query(MarketplaceInstallation).count()
        total_reviews = self.db.query(MarketplaceReview).filter(MarketplaceReview.is_active).count()
        return {
            "total_apps": total_apps,
            "total_categories": total_categories,
            "total_installs": total_installs,
            "total_reviews": total_reviews,
        }
