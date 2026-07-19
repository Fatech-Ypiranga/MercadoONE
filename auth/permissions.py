from utils.enums import UserProfile

READ = "read"
WRITE = "write"

MODULE_PERMISSIONS: dict[str, dict[UserProfile, set[str]]] = {
    "categories": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "products": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "customers": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ, WRITE},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "sales": {
        UserProfile.ADMIN: {READ, WRITE, "cancel", "discount"},
        UserProfile.GERENTE: {READ, WRITE, "cancel", "discount"},
        UserProfile.SUPERVISOR: {READ, WRITE, "cancel", "discount"},
        UserProfile.OPERADOR: {READ, WRITE},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "stock": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ, WRITE},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ, WRITE},
        UserProfile.COLABORADOR: {READ},
    },
    "reports": {
        UserProfile.ADMIN: {READ},
        UserProfile.GERENTE: {READ},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "users": {
        UserProfile.ADMIN: {READ, WRITE},
    },
    "audit": {
        UserProfile.ADMIN: {READ},
    },
    "suppliers": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "purchases": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ, WRITE},
        UserProfile.COLABORADOR: {READ},
    },
    "branches": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "stores": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ, WRITE},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
    "companies": {
        UserProfile.ADMIN: {READ, WRITE},
        UserProfile.GERENTE: {READ},
        UserProfile.SUPERVISOR: {READ},
        UserProfile.OPERADOR: {READ},
        UserProfile.CONFERENTE: {READ},
        UserProfile.COLABORADOR: {READ},
    },
}


def has_permission(profile: UserProfile, permission: str) -> bool:
    if ":" not in permission:
        return False

    module, action = permission.split(":", 1)
    module_perms = MODULE_PERMISSIONS.get(module, {})
    allowed_actions = module_perms.get(profile, set())
    return action in allowed_actions
