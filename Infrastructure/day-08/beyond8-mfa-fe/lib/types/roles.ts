export const ROLE_ADMIN = "ROLE_ADMIN";
export const ROLE_USER = "ROLE_USER";

export type UserRole = typeof ROLE_ADMIN | typeof ROLE_USER;

const normalizeRole = (role: string | null | undefined): string | null => {
  if (!role) return null;
  const upper = role.toUpperCase();

  if (upper === "ADMIN" || upper === ROLE_ADMIN) return ROLE_ADMIN;
  if (upper === "USER" || upper === ROLE_USER) return ROLE_USER;

  return upper;
};

export const hasAdminRole = (roles: string[]): boolean =>
  roles.some((role) => normalizeRole(role) === ROLE_ADMIN);

export const getPrimaryRole = (roles: string[]): UserRole | null => {
  if (hasAdminRole(roles)) return ROLE_ADMIN;
  if (roles.some((role) => normalizeRole(role) === ROLE_USER)) return ROLE_USER;
  return null;
};
