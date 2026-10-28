"""
permissions.py — Sistem scoping dan permission untuk hierarki PLN METRIK
Hierarki: super_admin → uid → up3 → ulp → verifikator
"""
from fastapi import HTTPException, status
from app.models import RoleEnum, User

# Role yang dianggap "admin-level" (bisa lihat semua)
ADMIN_ROLES = {RoleEnum.super_admin, RoleEnum.uid, RoleEnum.up3, RoleEnum.ulp}

# Role yang bisa membuat user, dan role apa yang boleh mereka buat
CAN_CREATE_ROLE = {
    RoleEnum.super_admin: [RoleEnum.uid, RoleEnum.up3, RoleEnum.ulp, RoleEnum.verifikator],
    RoleEnum.uid:         [RoleEnum.up3, RoleEnum.ulp, RoleEnum.verifikator],
    RoleEnum.up3:         [RoleEnum.ulp, RoleEnum.verifikator],
    RoleEnum.ulp:         [RoleEnum.verifikator],
}

# Role yang boleh upload batch
CAN_UPLOAD = {RoleEnum.super_admin, RoleEnum.up3}

# Role yang boleh assign verifikator (Pembagian Tugas)
CAN_ASSIGN = {RoleEnum.super_admin, RoleEnum.ulp}

# Role yang boleh manage alasan
CAN_MANAGE_REASONS = {RoleEnum.super_admin, RoleEnum.uid}

# Role yang boleh export
CAN_EXPORT = {RoleEnum.super_admin, RoleEnum.uid, RoleEnum.up3, RoleEnum.ulp}


def require_role(*roles: RoleEnum):
    """Raise 403 jika user tidak punya role yang diizinkan."""
    def check(current_user: User):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Role yang dibutuhkan: {[r.value for r in roles]}"
            )
        return current_user
    return check


def get_kode_scope(user: User) -> str | None:
    """
    Kembalikan prefix kode_unit untuk filtering data berdasarkan role.
    - super_admin: None (lihat semua)
    - uid/up3/ulp: kode_unit mereka (filter LIKE 'kode%')
    - verifikator: None (pakai assigned_to filter)
    """
    if user.role == RoleEnum.super_admin:
        return None  # lihat semua
    if user.role == RoleEnum.verifikator:
        return None  # scoped by assigned_to, bukan kode_unit
    return user.kode_unit


def apply_scope_filter(query, model, user: User):
    """
    Terapkan filter scope berdasarkan kode_unit user ke query SQLAlchemy.
    Model harus punya kolom 'kode_unit'.
    """
    kode = get_kode_scope(user)
    if kode:
        query = query.filter(model.kode_unit.like(f"{kode}%"))
    return query


def can_create_role(creator: User, target_role: RoleEnum) -> bool:
    """Cek apakah creator boleh membuat user dengan role target_role."""
    allowed = CAN_CREATE_ROLE.get(creator.role, [])
    return target_role in allowed


def validate_kode_unit_hierarchy(creator: User, new_kode_unit: str | None) -> bool:
    """
    Validasi kode_unit user baru harus diawali kode_unit creator.
    Contoh: UP3 (171) boleh buat ULP (17100, 17101) tapi tidak boleh buat kode 151xx.
    Super admin boleh buat kode apapun.
    """
    if creator.role == RoleEnum.super_admin:
        return True
    if not creator.kode_unit:
        return True  # creator tanpa kode bebas
    if not new_kode_unit:
        return True  # verifikator tidak butuh kode
    return new_kode_unit.startswith(creator.kode_unit)
