"""
auth.py
Middleware de autenticacion para MODELIA.

Verifica el JWT de Supabase en cada peticion protegida llamando a
auth.get_user(token) con la service-role key del servidor. Si el token es
valido y el email pertenece al dominio permitido, cuelga la info del usuario
en flask.g.user y deja pasar; si no, devuelve 401.

El backend NO confia en el gating del navegador: cualquier endpoint protegido
exige un Authorization: Bearer <jwt> valido.
"""

import functools
import logging
import os

from flask import g, jsonify, request
from supabase import create_client

log = logging.getLogger("auth")

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://pntipdspiivffvxfyshg.supabase.co",
).strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", ""
).strip()
ALLOWED_EMAIL_DOMAIN = os.environ.get(
    "ALLOWED_EMAIL_DOMAIN", "cardenas-grancanaria.com"
).strip().lower()


class _LazyAdminClient:
    """Difiere create_client hasta el primer uso: una instalacion rota de
    supabase no debe poder tumbar la app al importarse este modulo."""
    _real = None

    def __getattr__(self, name):
        if _LazyAdminClient._real is None:
            if not SUPABASE_SERVICE_ROLE_KEY:
                raise RuntimeError(
                    "SUPABASE_SERVICE_ROLE_KEY no configurada; "
                    "anade la variable de entorno en Railway."
                )
            _LazyAdminClient._real = create_client(
                SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
            )
        return getattr(_LazyAdminClient._real, name)


_admin = _LazyAdminClient()


def _extract_token(req) -> str | None:
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip() or None
    return None


def verify_token(token: str):
    """Valida el JWT contra Supabase. Devuelve dict de usuario o None."""
    try:
        result = _admin.auth.get_user(token)
        user = getattr(result, "user", None)
        if user is None:
            return None

        email = (getattr(user, "email", "") or "").lower().strip()
        if not email:
            return None

        # Defensa en profundidad: aunque el trigger SQL bloquea el alta de
        # dominios no permitidos, el backend tambien lo verifica por si
        # alguien rotara el trigger o cambiara la config.
        if not email.endswith("@" + ALLOWED_EMAIL_DOMAIN):
            log.warning(f"[AUTH] dominio no autorizado: {email}")
            return None

        # Supabase devuelve email_confirmed_at solo si el usuario completo
        # la verificacion (en passwordless con OTP esto ocurre al verificar
        # el codigo). Si no esta confirmado, no le dejamos pasar.
        confirmed_at = getattr(user, "email_confirmed_at", None)
        if not confirmed_at:
            log.warning(f"[AUTH] email no confirmado: {email}")
            return None

        return {
            "id": getattr(user, "id", None),
            "email": email,
        }
    except Exception as exc:
        log.warning(f"[AUTH] verificacion fallida ({type(exc).__name__}: {exc})")
        return None


def require_auth(fn):
    """Decorator: 401 salvo que la request lleve un JWT Supabase valido."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token(request)
        if not token:
            return jsonify({"error": "Falta token de autenticacion."}), 401
        user = verify_token(token)
        if user is None:
            return jsonify({"error": "Sesion invalida o expirada."}), 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def cleanup_orphan_user(email: str) -> dict:
    """Borra un usuario "huerfano" si existe.

    Un huerfano es un user en auth.users que tiene email_confirmed_at
    null Y last_sign_in_at null. Eso solo pasa cuando alguien empezo el
    proceso de OTP/signup y nunca llego a entrar, dejando una entrada
    incompleta que rompe los siguientes intentos de signInWithOtp con
    el mensaje engañoso "Email address is invalid".

    SOLO toca usuarios huerfanos del dominio permitido. No puede usarse
    para borrar cuentas activas.

    Devuelve {ok, deleted, reason}.
    """
    email = (email or "").strip().lower()
    if not email or not email.endswith("@" + ALLOWED_EMAIL_DOMAIN):
        return {"ok": False, "deleted": False, "reason": "dominio_no_permitido"}
    try:
        resp = _admin.auth.admin.list_users()
        users = resp if isinstance(resp, list) else getattr(resp, "users", []) or []
        target = None
        for u in users:
            u_email = (getattr(u, "email", "") or "").lower()
            if u_email == email:
                target = u
                break
        if target is None:
            return {"ok": True, "deleted": False, "reason": "no_existe"}
        confirmed = getattr(target, "email_confirmed_at", None)
        last_sign_in = getattr(target, "last_sign_in_at", None)
        if confirmed is not None or last_sign_in is not None:
            return {"ok": False, "deleted": False, "reason": "cuenta_activa"}
        _admin.auth.admin.delete_user(getattr(target, "id"))
        log.info(f"[AUTH] huerfano eliminado: {email}")
        return {"ok": True, "deleted": True, "reason": "huerfano_limpiado"}
    except Exception as exc:
        log.warning(f"[AUTH] cleanup_orphan_user fail: {exc}")
        return {"ok": False, "deleted": False, "reason": "error_interno"}
