import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    users: Mapped[list["User"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    memberships: Mapped[list["ShopMembership"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    settings: Mapped["ShopSettings"] = relationship(back_populates="shop", uselist=False, cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="owner")
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    shop: Mapped[Shop] = relationship(back_populates="users")
    memberships: Mapped[list["ShopMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ShopMembership(Base):
    __tablename__ = "shop_memberships"
    __table_args__ = (UniqueConstraint("shop_id", "user_id", name="uq_shop_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="staff")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    shop: Mapped[Shop] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), unique=True, index=True)
    store_name: Mapped[str] = mapped_column(String(160), default="SmartBill Store")
    phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    invoice_prefix: Mapped[str] = mapped_column(String(20), default="INV-")
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)
    theme: Mapped[str] = mapped_column(String(10), default="light")
    next_invoice_number: Mapped[int] = mapped_column(Integer, default=1)
    shop: Mapped[Shop] = relationship(back_populates="settings")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100), default="General")
    unit: Mapped[str] = mapped_column(String(30), default="pcs")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    min_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=10)
    is_active: Mapped[bool] = mapped_column(default=True)
    shop: Mapped[Shop] = relationship(back_populates="products")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("shop_id", "invoice_number", name="uq_invoice_shop_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), index=True)
    customer_name: Mapped[str] = mapped_column(String(160), default="User")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(30), default="Cash")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    shop: Mapped[Shop] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(180))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_extra: Mapped[bool] = mapped_column(default=False)
    invoice: Mapped[Invoice] = relationship(back_populates="items")


class ShareToken(Base):
    __tablename__ = "share_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(50), default="")
    target_id: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def create_app() -> Flask:
    app = Flask(__name__)
    logger = logging.getLogger("smartbill")
    logging.basicConfig(level=os.environ.get("SMARTBILL_LOG_LEVEL", "INFO").upper())
    default_database_url = f"sqlite:///{(Path(__file__).resolve().parent / 'smartbill.db').as_posix()}"
    app.config.update(
        SECRET_KEY=os.environ.get("SMARTBILL_SECRET_KEY") or secrets.token_urlsafe(32),
        DATABASE_URL=os.environ.get("DATABASE_URL", default_database_url),
        PUBLIC_BASE_URL=os.environ.get("SMARTBILL_PUBLIC_URL", "").strip().rstrip("/"),
        SHARE_LINK_HOURS=int(os.environ.get("SHARE_LINK_HOURS", "24")),
        MAX_CONTENT_LENGTH=256 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SMARTBILL_SECURE_COOKIES", "").lower() == "true",
        RATELIMIT_STORAGE_URI=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    )
    if app.config["PUBLIC_BASE_URL"]:
        public_url = urlparse(app.config["PUBLIC_BASE_URL"])
        if public_url.scheme not in {"http", "https"} or not public_url.netloc:
            raise ValueError("SMARTBILL_PUBLIC_URL must be a complete http(s) URL.")
        if public_url.scheme != "https" and public_url.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("SMARTBILL_PUBLIC_URL must use HTTPS outside local development.")

    engine = create_engine(app.config["DATABASE_URL"], future=True)
    limiter = Limiter(key_func=get_remote_address, app=app, storage_uri=app.config["RATELIMIT_STORAGE_URI"],
                      default_limits=["300 per minute"])
    session_factory = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
    if os.environ.get("SMARTBILL_AUTO_CREATE_SCHEMA", "true").lower() == "true":
        Base.metadata.create_all(engine)

    def db():
        return session_factory()

    def csrf_token():
        token = session.get("_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf"] = token
        return token

    @app.context_processor
    def inject_template_values():
        return {"csrf_token": csrf_token()}

    @app.before_request
    def validate_csrf():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.endpoint not in {"setup", "login"}:
            expected = session.get("_csrf")
            supplied = request.headers.get("X-CSRF-Token") or request.form.get("_csrf")
            if expected and not secrets.compare_digest(expected, supplied or ""):
                return jsonify({"error": "Invalid security token. Refresh and try again."}), 403

    @app.teardown_appcontext
    def remove_session(_exception=None):
        session_factory.remove()

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        user = db().get(User, user_id)
        if not user or session.get("session_version") != user.session_version:
            session.clear()
            return None
        return user

    def current_membership():
        user = current_user()
        if not user:
            return None
        shop_id = session.get("active_shop_id", user.shop_id)
        membership = db().scalar(select(ShopMembership).where(
            ShopMembership.user_id == user.id,
            ShopMembership.shop_id == shop_id,
        ))
        if membership:
            return membership
        if shop_id == user.shop_id:
            membership = ShopMembership(user_id=user.id, shop_id=user.shop_id, role=user.role or "owner")
            session_db = db()
            session_db.add(membership)
            session_db.commit()
            return membership
        return None

    def current_shop_id():
        membership = current_membership()
        return membership.shop_id if membership else None

    def current_shop():
        shop_id = current_shop_id()
        return db().get(Shop, shop_id) if shop_id else None

    def private_route(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user():
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def role_required(*roles):
        allowed = set(roles)

        def decorator(view):
            @wraps(view)
            @private_route
            def wrapped(*args, **kwargs):
                membership = current_membership()
                if not membership or membership.role not in allowed:
                    if request.path.startswith("/api/"):
                        return jsonify({"error": "You do not have permission for this action"}), 403
                    return jsonify({"error": "You do not have permission for this action"}), 403
                return view(*args, **kwargs)
            return wrapped
        return decorator

    def json_error(message, status=400):
        return jsonify({"error": message}), status

    def audit(session_db, action, target_type="", target_id=""):
        user = current_user()
        shop_id = current_shop_id()
        if not shop_id:
            return
        session_db.add(AuditEvent(
            shop_id=shop_id,
            user_id=user.id if user else None,
            action=action,
            target_type=target_type[:50],
            target_id=str(target_id)[:80],
        ))

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        return error

    @app.errorhandler(500)
    def handle_server_error(error):
        logger.exception("Unhandled request error", exc_info=error)
        if request.path.startswith("/api/"):
            return jsonify({"error": "An unexpected server error occurred"}), 500
        return "An unexpected server error occurred.", 500

    def money(value):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Amount must be a valid number")
        if not result.is_finite() or result < 0 or result > Decimal("9999999999.99"):
            raise ValueError("Amount is outside the allowed range")
        return result.quantize(Decimal("0.01"))

    def parse_quantity(value, allow_zero=False):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Quantity must be a valid number")
        if not result.is_finite() or (result < 0 if allow_zero else result <= 0) or result > Decimal("999999999.999"):
            raise ValueError("Quantity is outside the allowed range")
        rounded = result.quantize(Decimal("0.001"))
        if rounded != result:
            raise ValueError("Quantity supports up to three decimal places")
        return rounded

    def product_json(product):
        return {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "unit": product.unit,
            "price": float(product.price),
            "stock": float(product.stock),
            "minStock": float(product.min_stock),
        }

    def invoice_json(invoice):
        created_at = invoice.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        return {
            "internalId": invoice.id,
            "id": invoice.invoice_number,
            "date": created_at.isoformat(),
            "customerName": invoice.customer_name,
            "subtotal": float(invoice.subtotal),
            "discount": float(invoice.discount),
            "total": float(invoice.total),
            "paymentMethod": invoice.payment_method,
            "items": [
                {
                    "productId": item.product_id,
                    "name": item.product_name,
                    "price": float(item.unit_price),
                    "qty": float(item.quantity),
                    "total": float(item.line_total),
                    "isExtra": item.is_extra,
                }
                for item in invoice.items
            ],
        }

    def create_shop_account(session_db, shop_name, name, email, password):
        if not shop_name or not name or not email or len(password) < 10:
            raise ValueError("Shop name, owner name, email and a password of at least 10 characters are required.")
        if session_db.scalar(select(User).where(User.email == email)):
            raise ValueError("An account with this email already exists.")
        shop = Shop(name=shop_name)
        shop.settings = ShopSettings(store_name=shop_name)
        shop.products = [
            Product(name="Wireless Ergonomic Mouse", category="Electronics", unit="pcs", price=1499, stock=45, min_stock=10),
            Product(name="Mechanical RGB Keyboard", category="Electronics", unit="pcs", price=3299, stock=18, min_stock=5),
            Product(name="USB-C Fast Charger 65W", category="Electronics", unit="pcs", price=1199, stock=3, min_stock=8),
            Product(name="Premium Cotton T-Shirt (M)", category="Apparel", unit="pcs", price=699, stock=60, min_stock=15),
            Product(name="Dark Roasted Coffee Beans 500g", category="Grocery", unit="pack", price=599, stock=30, min_stock=10),
        ]
        user = User(name=name, email=email, password_hash=generate_password_hash(password), shop=shop, role="owner")
        session_db.add(user)
        session_db.commit()
        session_db.add(ShopMembership(user_id=user.id, shop_id=shop.id, role="owner"))
        session_db.commit()

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/setup", methods=["GET", "POST"])
    @limiter.limit("5 per minute", methods=["POST"])
    def setup():
        session_db = db()
        if session_db.scalar(select(User.id).limit(1)):
            return redirect(url_for("login"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            shop_name = request.form.get("shop_name", "").strip()
            try:
                create_shop_account(session_db, shop_name, name, email, password)
            except ValueError as error:
                return render_template("setup.html", error=str(error)), 400
            return redirect(url_for("login"))
        return render_template("setup.html")

    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("5 per minute", methods=["POST"])
    def register():
        session_db = db()
        if request.method == "POST":
            try:
                create_shop_account(
                    session_db,
                    request.form.get("shop_name", "").strip(),
                    request.form.get("name", "").strip(),
                    request.form.get("email", "").strip().lower(),
                    request.form.get("password", ""),
                )
            except ValueError as error:
                return render_template("setup.html", error=str(error), registration=True), 400
            return redirect(url_for("login"))
        return render_template("setup.html", registration=True)

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute", methods=["POST"])
    def login():
        session_db = db()
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = session_db.scalar(select(User).where(User.email == email))
            now = datetime.now(timezone.utc)
            locked_until = user.locked_until if user and user.locked_until and user.locked_until.tzinfo else (
                user.locked_until.replace(tzinfo=timezone.utc) if user and user.locked_until else None
            )
            if user and locked_until and locked_until > now:
                return render_template("login.html", error="This account is temporarily locked. Try again later."), 423
            if not user or not check_password_hash(user.password_hash, password):
                if user:
                    user.failed_login_attempts += 1
                    if user.failed_login_attempts >= 5:
                        user.locked_until = now + timedelta(minutes=15)
                        user.failed_login_attempts = 0
                    session_db.commit()
                return render_template("login.html", error="Invalid email or password."), 401
            user.failed_login_attempts = 0
            user.locked_until = None
            user.session_version += 1
            session_db.commit()
            session.clear()
            session["user_id"] = user.id
            session["active_shop_id"] = user.shop_id
            session["session_version"] = user.session_version
            session["_csrf"] = secrets.token_urlsafe(32)
            return redirect(request.form.get("next") or url_for("dashboard"))
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        if not session_db.scalar(select(User.id).limit(1)):
            return redirect(url_for("setup"))
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @private_route
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/products")
    @private_route
    def products():
        return render_template("products.html")

    @app.route("/billing")
    @private_route
    def billing():
        return render_template("billing.html")

    @app.route("/sales")
    @private_route
    def sales():
        return render_template("sales.html")

    @app.route("/profile")
    @private_route
    def profile():
        return render_template("profile.html")

    @app.route("/invoice")
    @private_route
    def invoice():
        return render_template("invoice.html")

    @app.get("/api/me")
    @private_route
    def me():
        user = current_user()
        session_db = db()
        shop = current_shop()
        settings = session_db.scalar(select(ShopSettings).where(ShopSettings.shop_id == shop.id).with_for_update())
        membership = current_membership()
        memberships = session_db.scalars(select(ShopMembership).where(ShopMembership.user_id == user.id)).all()
        return jsonify({"user": {"id": user.id, "name": user.name, "email": user.email, "role": membership.role},
                        "shop": {"id": shop.id, "name": shop.name, "role": membership.role},
                        "settings": settings_json(settings),
                        "memberships": [{"shopId": item.shop_id, "shopName": item.shop.name, "role": item.role} for item in memberships],
                        "csrfToken": csrf_token()})

    @app.post("/api/shop/switch")
    @private_route
    def api_switch_shop():
        payload = request.get_json(silent=True) or {}
        try:
            shop_id = int(payload.get("shopId"))
        except (TypeError, ValueError):
            return json_error("Shop selection is invalid")
        membership = db().scalar(select(ShopMembership).where(
            ShopMembership.user_id == current_user().id,
            ShopMembership.shop_id == shop_id,
        ))
        if not membership:
            return json_error("You are not a member of this shop", 403)
        session["active_shop_id"] = shop_id
        return jsonify({"ok": True, "shopId": shop_id, "role": membership.role})

    def staff_json(membership):
        return {
            "id": membership.user.id,
            "name": membership.user.name,
            "email": membership.user.email,
            "role": membership.role,
            "createdAt": membership.created_at.isoformat(),
        }

    @app.get("/api/staff")
    @role_required("owner", "manager")
    def api_staff():
        shop_id = current_shop_id()
        memberships = db().scalars(select(ShopMembership).where(ShopMembership.shop_id == shop_id).order_by(ShopMembership.created_at)).all()
        return jsonify({"staff": [staff_json(item) for item in memberships]})

    @app.post("/api/staff")
    @role_required("owner")
    def api_add_staff():
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()[:120]
        email = str(payload.get("email", "")).strip().lower()[:255]
        password = str(payload.get("password", ""))
        role = str(payload.get("role", "staff")).strip().lower()
        if not name or "@" not in email or len(password) < 10 or role not in {"manager", "cashier", "staff"}:
            return json_error("Name, valid email, 10-character password and a valid role are required")
        session_db = db()
        if session_db.scalar(select(User).where(User.email == email)):
            return json_error("An account with this email already exists")
        user = User(shop_id=current_shop_id(), name=name, email=email, password_hash=generate_password_hash(password), role=role)
        session_db.add(user)
        session_db.flush()
        session_db.add(ShopMembership(user_id=user.id, shop_id=current_shop_id(), role=role))
        audit(session_db, "staff.created", "user", user.id)
        session_db.commit()
        return jsonify({"staff": staff_json(session_db.scalar(select(ShopMembership).where(
            ShopMembership.user_id == user.id, ShopMembership.shop_id == current_shop_id())))}), 201

    @app.put("/api/staff/<int:user_id>")
    @role_required("owner")
    def api_update_staff(user_id):
        payload = request.get_json(silent=True) or {}
        role = str(payload.get("role", "")).strip().lower()
        if role not in {"manager", "cashier", "staff"}:
            return json_error("Invalid staff role")
        session_db = db()
        membership = session_db.scalar(select(ShopMembership).where(
            ShopMembership.user_id == user_id, ShopMembership.shop_id == current_shop_id()))
        if not membership:
            return json_error("Staff member not found", 404)
        membership.role = role
        membership.user.role = role
        audit(session_db, "staff.role_changed", "user", user_id)
        session_db.commit()
        return jsonify({"staff": staff_json(membership)})

    @app.delete("/api/staff/<int:user_id>")
    @role_required("owner")
    def api_remove_staff(user_id):
        session_db = db()
        membership = session_db.scalar(select(ShopMembership).where(
            ShopMembership.user_id == user_id, ShopMembership.shop_id == current_shop_id()))
        if not membership or membership.role == "owner":
            return json_error("Staff member not found", 404)
        session_db.delete(membership)
        audit(session_db, "staff.removed", "user", user_id)
        session_db.commit()
        return jsonify({"ok": True})

    def settings_json(settings):
        return {
            "storeName": settings.store_name,
            "phone": settings.phone,
            "address": settings.address,
            "invoicePrefix": settings.invoice_prefix,
            "lowStockThreshold": settings.low_stock_threshold,
            "theme": settings.theme,
        }

    @app.get("/api/products")
    @private_route
    def api_products():
        shop_id = current_shop_id()
        session_db = db()
        products = session_db.scalars(select(Product).where(Product.shop_id == shop_id, Product.is_active.is_(True)).order_by(Product.name)).all()
        return jsonify({"products": [product_json(product) for product in products]})

    @app.post("/api/products")
    @role_required("owner", "manager")
    def api_create_product():
        shop_id = current_shop_id()
        payload = request.get_json(silent=True) or {}
        try:
            name = str(payload.get("name", "")).strip()
            category = str(payload.get("category", "General")).strip() or "General"
            price = money(payload.get("price"))
            stock = parse_quantity(payload.get("stock", 0), allow_zero=True)
            min_stock = parse_quantity(payload.get("minStock", 10), allow_zero=True)
            if not name or len(name) > 180 or stock < 0 or min_stock < 0:
                raise ValueError("Invalid product details")
        except (TypeError, ValueError, InvalidOperation):
            return json_error("Product details are invalid")
        session_db = db()
        product = Product(shop_id=shop_id, name=name, category=category, unit=str(payload.get("unit", "pcs"))[:30], price=price, stock=stock, min_stock=min_stock)
        session_db.add(product)
        audit(session_db, "product.created", "product", product.name)
        session_db.commit()
        return jsonify({"product": product_json(product)}), 201

    @app.put("/api/products/<int:product_id>")
    @role_required("owner", "manager")
    def api_update_product(product_id):
        shop_id = current_shop_id()
        session_db = db()
        product = session_db.scalar(select(Product).where(Product.id == product_id, Product.shop_id == shop_id, Product.is_active.is_(True)).with_for_update())
        if not product:
            return json_error("Product not found", 404)
        payload = request.get_json(silent=True) or {}
        try:
            name = str(payload.get("name", "")).strip()
            price = money(payload.get("price"))
            stock = parse_quantity(payload.get("stock", 0), allow_zero=True)
            min_stock = parse_quantity(payload.get("minStock", 10), allow_zero=True)
            if not name or len(name) > 180 or stock < 0 or min_stock < 0:
                raise ValueError
        except (TypeError, ValueError, InvalidOperation):
            return json_error("Product details are invalid")
        product.name = name
        product.category = str(payload.get("category", "General")).strip() or "General"
        product.unit = str(payload.get("unit", "pcs"))[:30]
        product.price = price
        product.stock = stock
        product.min_stock = min_stock
        audit(session_db, "product.updated", "product", product.id)
        session_db.commit()
        return jsonify({"product": product_json(product)})

    @app.delete("/api/products/<int:product_id>")
    @role_required("owner", "manager")
    def api_delete_product(product_id):
        shop_id = current_shop_id()
        session_db = db()
        product = session_db.scalar(select(Product).where(Product.id == product_id, Product.shop_id == shop_id, Product.is_active.is_(True)))
        if not product:
            return json_error("Product not found", 404)
        product.is_active = False
        audit(session_db, "product.archived", "product", product.id)
        session_db.commit()
        return jsonify({"ok": True})

    @app.get("/api/settings")
    @private_route
    def api_settings():
        settings = db().scalar(select(ShopSettings).where(ShopSettings.shop_id == current_shop_id()))
        return jsonify({"settings": settings_json(settings)})

    @app.put("/api/settings")
    @role_required("owner", "manager")
    def api_update_settings():
        shop_id = current_shop_id()
        payload = request.get_json(silent=True) or {}
        session_db = db()
        settings = session_db.scalar(select(ShopSettings).where(ShopSettings.shop_id == shop_id).with_for_update())
        settings.store_name = str(payload.get("storeName", settings.store_name)).strip()[:160] or settings.store_name
        settings.phone = str(payload.get("phone", settings.phone)).strip()[:40]
        settings.address = str(payload.get("address", settings.address)).strip()[:2000]
        settings.invoice_prefix = str(payload.get("invoicePrefix", settings.invoice_prefix)).strip()[:20] or "INV-"
        try:
            settings.low_stock_threshold = max(0, int(payload.get("lowStockThreshold", settings.low_stock_threshold)))
        except (TypeError, ValueError):
            return json_error("Low stock threshold must be a whole number")
        settings.theme = "dark" if payload.get("theme") == "dark" else "light"
        audit(session_db, "settings.updated", "shop", shop_id)
        session_db.commit()
        return jsonify({"settings": settings_json(settings)})

    @app.put("/api/profile/password")
    @private_route
    def api_change_password():
        user = current_user()
        payload = request.get_json(silent=True) or {}
        current_password = str(payload.get("currentPassword", ""))
        new_password = str(payload.get("newPassword", ""))
        if not check_password_hash(user.password_hash, current_password):
            return json_error("Current password is incorrect", 400)
        if len(new_password) < 10:
            return json_error("New password must be at least 10 characters", 400)
        session_db = db()
        user.password_hash = generate_password_hash(new_password)
        user.session_version += 1
        session_db.commit()
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/backup")
    @role_required("owner")
    def api_backup():
        shop_id = current_shop_id()
        session_db = db()
        settings = session_db.scalar(select(ShopSettings).where(ShopSettings.shop_id == shop_id).with_for_update())
        products = session_db.scalars(select(Product).where(Product.shop_id == shop_id, Product.is_active.is_(True))).all()
        invoices = session_db.scalars(select(Invoice).where(Invoice.shop_id == shop_id).order_by(Invoice.created_at)).all()
        return jsonify({
            "version": 1,
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "settings": settings_json(settings),
            "products": [product_json(product) for product in products],
            "sales": [invoice_json(invoice) for invoice in invoices],
        })

    @app.post("/api/migrate/local")
    @role_required("owner")
    def api_migrate_local():
        shop_id = current_shop_id()
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload.get("products", []), list) or not isinstance(payload.get("sales", []), list):
            return json_error("Migration data must contain products and sales arrays")
        session_db = db()
        existing_products = session_db.scalars(select(Product).where(Product.shop_id == shop_id)).all()
        product_by_name = {product.name.casefold(): product for product in existing_products}
        imported_products = 0
        for raw in payload["products"][:5000]:
            name = str(raw.get("name", "")).strip()[:180]
            if not name or name.casefold() in product_by_name:
                continue
            try:
                price = money(raw.get("price", 0))
                stock = max(0, int(raw.get("stock", 0)))
                min_stock = max(0, int(raw.get("minStock", 10)))
            except (TypeError, ValueError, InvalidOperation):
                continue
            product = Product(shop_id=shop_id, name=name, category=str(raw.get("category", "General")).strip()[:100] or "General",
                              unit=str(raw.get("unit", "pcs"))[:30], price=price, stock=stock, min_stock=min_stock)
            session_db.add(product)
            product_by_name[name.casefold()] = product
            imported_products += 1
        session_db.flush()
        existing_numbers = set(session_db.scalars(select(Invoice.invoice_number).where(Invoice.shop_id == shop_id)).all())
        imported_invoices = 0
        settings = session_db.scalar(select(ShopSettings).where(ShopSettings.shop_id == shop_id).with_for_update())
        for raw in payload["sales"][:5000]:
            number = str(raw.get("id", "")).strip()[:40]
            if not number or number in existing_numbers or not isinstance(raw.get("items"), list):
                continue
            items = []
            subtotal = Decimal("0.00")
            for item in raw["items"][:200]:
                try:
                    quantity = parse_quantity(item.get("qty"))
                    price = money(item.get("price", 0))
                except (TypeError, ValueError, InvalidOperation):
                    continue
                if quantity <= 0:
                    continue
                name = str(item.get("name", "")).strip()[:180] or "Imported item"
                product = product_by_name.get(name.casefold()) if not item.get("isExtra") else None
                line_total = (price * quantity).quantize(Decimal("0.01"))
                subtotal += line_total
                items.append((product, name, price, quantity, line_total, product is None))
            if not items:
                continue
            try:
                discount = min(money(raw.get("discount", 0)), subtotal)
            except (TypeError, ValueError, InvalidOperation):
                discount = Decimal("0.00")
            invoice = Invoice(shop_id=shop_id, invoice_number=number, customer_name=str(raw.get("customerName", "User"))[:160] or "User",
                              subtotal=subtotal, discount=discount, total=subtotal - discount, payment_method="Cash")
            session_db.add(invoice)
            session_db.flush()
            for product, name, price, quantity, line_total, is_extra in items:
                invoice.items.append(InvoiceItem(product_id=product.id if product else None, product_name=name, unit_price=price,
                                                 quantity=quantity, line_total=line_total, is_extra=is_extra))
            existing_numbers.add(number)
            imported_invoices += 1
        if isinstance(payload.get("settings"), dict):
            raw_settings = payload["settings"]
            settings.store_name = str(raw_settings.get("storeName", settings.store_name)).strip()[:160] or settings.store_name
            settings.phone = str(raw_settings.get("phone", settings.phone)).strip()[:40]
            settings.address = str(raw_settings.get("address", settings.address)).strip()[:2000]
        session_db.commit()
        return jsonify({"importedProducts": imported_products, "importedInvoices": imported_invoices})

    @app.get("/api/invoices")
    @private_route
    def api_invoices():
        shop_id = current_shop_id()
        session_db = db()
        query = select(Invoice).where(Invoice.shop_id == shop_id).order_by(Invoice.created_at.desc())
        invoices = session_db.scalars(query).all()
        return jsonify({"invoices": [invoice_json(invoice) for invoice in invoices]})

    @app.get("/api/invoices/<int:invoice_id>")
    @private_route
    def api_invoice(invoice_id):
        invoice = db().scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.shop_id == current_shop_id()))
        if not invoice:
            return json_error("Invoice not found", 404)
        return jsonify({"invoice": invoice_json(invoice)})

    @app.post("/api/invoices")
    @private_route
    def api_create_invoice():
        shop_id = current_shop_id()
        payload = request.get_json(silent=True) or {}
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items or len(raw_items) > 200:
            return json_error("Invoice must contain between 1 and 200 items")
        session_db = db()
        settings = session_db.scalar(select(ShopSettings).where(ShopSettings.shop_id == shop_id).with_for_update())
        invoice_items = []
        subtotal = Decimal("0.00")
        try:
            for raw in raw_items:
                item_quantity = parse_quantity(raw.get("qty"))
                if raw.get("isExtra"):
                    name = str(raw.get("name", "")).strip()
                    price = money(raw.get("price"))
                    product = None
                else:
                    product_id = int(raw.get("productId"))
                    product = session_db.scalar(select(Product).where(
                        Product.id == product_id,
                        Product.shop_id == shop_id,
                        Product.is_active.is_(True),
                    ).with_for_update())
                    if not product or product.stock < item_quantity:
                        return json_error(f"Insufficient stock for product {product_id}", 409)
                    name, price = product.name, Decimal(product.price)
                line_total = (price * item_quantity).quantize(Decimal("0.01"))
                subtotal += line_total
                invoice_items.append((product, name[:180], price, item_quantity, line_total, bool(raw.get("isExtra"))))
            discount = money(payload.get("discount", 0))
            if discount > subtotal:
                return json_error("Discount cannot exceed subtotal")
        except (TypeError, ValueError, InvalidOperation):
            return json_error("Invoice items are invalid")
        invoice_number = f"{settings.invoice_prefix}{settings.next_invoice_number:06d}"
        settings.next_invoice_number += 1
        invoice = Invoice(shop_id=shop_id, invoice_number=invoice_number, customer_name=str(payload.get("customerName", "User")).strip()[:160] or "User",
                          subtotal=subtotal, discount=discount, total=subtotal - discount, payment_method="Cash")
        session_db.add(invoice)
        session_db.flush()
        for product, name, price, quantity, line_total, is_extra in invoice_items:
            if product:
                product.stock -= quantity
            invoice.items.append(InvoiceItem(product_id=product.id if product else None, product_name=name, unit_price=price, quantity=quantity, line_total=line_total, is_extra=is_extra))
        audit(session_db, "invoice.created", "invoice", invoice.invoice_number)
        session_db.commit()
        return jsonify({"invoice": invoice_json(invoice)}), 201

    @app.delete("/api/invoices/<int:invoice_id>")
    @role_required("owner", "manager")
    def api_delete_invoice(invoice_id):
        session_db = db()
        invoice = session_db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.shop_id == current_shop_id()))
        if not invoice:
            return json_error("Invoice not found", 404)
        session_db.delete(invoice)
        audit(session_db, "invoice.deleted", "invoice", invoice.invoice_number)
        session_db.commit()
        return jsonify({"ok": True})

    @app.post("/api/invoices/<int:invoice_id>/share")
    @role_required("owner", "manager", "cashier")
    def api_share_invoice(invoice_id):
        session_db = db()
        invoice = session_db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.shop_id == current_shop_id()))
        if not invoice:
            return json_error("Invoice not found", 404)
        public_base_url = app.config["PUBLIC_BASE_URL"]
        if not public_base_url:
            request_host = request.host_url.rstrip("/")
            parsed_host = urlparse(request_host)
            if parsed_host.hostname in {"localhost", "127.0.0.1", "::1"}:
                return json_error(
                    "QR sharing needs a public HTTPS URL. Set SMARTBILL_PUBLIC_URL before generating a QR code.",
                    503,
                )
        raw_token = secrets.token_urlsafe(32)
        share = ShareToken(invoice_id=invoice.id, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                           expires_at=datetime.now(timezone.utc) + timedelta(hours=app.config["SHARE_LINK_HOURS"]))
        session_db.add(share)
        audit(session_db, "invoice.share_created", "invoice", invoice.invoice_number)
        session_db.commit()
        if public_base_url:
            share_url = f"{public_base_url}{url_for('public_invoice', token=raw_token)}"
        else:
            share_url = f"{request_host}{url_for('public_invoice', token=raw_token)}"
        return jsonify({"url": share_url, "expiresAt": share.expires_at.isoformat()})

    @app.get("/s/<token>")
    def public_invoice(token):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        share = db().scalar(select(ShareToken).where(ShareToken.token_hash == token_hash))
        now = datetime.now(timezone.utc)
        expires_at = share.expires_at.replace(tzinfo=timezone.utc) if share and share.expires_at.tzinfo is None else (share.expires_at if share else now)
        if not share or share.revoked_at or expires_at <= now:
            return render_template("share.html", bill_data=None), 404
        invoice = db().get(Invoice, share.invoice_id)
        settings = db().scalar(select(ShopSettings).where(ShopSettings.shop_id == invoice.shop_id))
        data = {"invoice": invoice_json(invoice), "store": settings_json(settings)}
        return render_template("share.html", bill_data=data, bill_id=invoice.invoice_number)

    @app.get("/api/dashboard")
    @private_route
    def api_dashboard():
        shop_id = current_shop_id()
        session_db = db()
        invoices = session_db.scalars(select(Invoice).where(Invoice.shop_id == shop_id).order_by(Invoice.created_at.desc())).all()
        products = session_db.scalars(select(Product).where(Product.shop_id == shop_id, Product.is_active.is_(True))).all()
        local_zone = ZoneInfo("Asia/Kolkata")
        today = datetime.now(local_zone).date()
        today_sales = sum((
            invoice.total for invoice in invoices
            if invoice.created_at.replace(tzinfo=timezone.utc).astimezone(local_zone).date() == today
        ), Decimal("0"))
        top_products = {}
        for invoice in invoices:
            for item in invoice.items:
                if item.is_extra:
                    continue
                entry = top_products.setdefault(item.product_name, {"name": item.product_name, "qty": 0, "amount": Decimal("0")})
                entry["qty"] += item.quantity
                entry["amount"] += item.line_total
        top_products = sorted(top_products.values(), key=lambda item: (-item["qty"], -item["amount"]))[:5]
        return jsonify({"todaySales": float(today_sales), "totalSales": float(sum((invoice.total for invoice in invoices), Decimal("0"))),
                        "totalBills": len(invoices),
                        "lowStock": sum(0 < product.stock <= product.min_stock for product in products),
                        "outOfStock": sum(product.stock <= 0 for product in products),
                        "invoices": [invoice_json(invoice) for invoice in invoices[:5]],
                        "salesHistory": [invoice_json(invoice) for invoice in invoices],
                        "topProducts": [{"name": item["name"], "qty": float(item["qty"]), "amount": float(item["amount"])} for item in top_products],
                        "products": [product_json(product) for product in products]})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true", host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
