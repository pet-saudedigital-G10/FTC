export const apiRoutes = {
  adminUsers:
    process.env.NEXT_PUBLIC_ADMIN_USERS_PATH ?? "/api/admin/users/",
  adminLogin:
    process.env.NEXT_PUBLIC_ADMIN_LOGIN_PATH ?? "/api/admin/auth/login/",
  adminRefresh:
    process.env.NEXT_PUBLIC_ADMIN_REFRESH_PATH ?? "/api/admin/auth/refresh/",
  adminLogout:
    process.env.NEXT_PUBLIC_ADMIN_LOGOUT_PATH ?? "/api/admin/auth/logout/",
  adminMe:
    process.env.NEXT_PUBLIC_ADMIN_ME_PATH ?? "/api/admin/auth/me/",
  filaRegistros:
    process.env.NEXT_PUBLIC_FILA_REGISTROS_PATH ?? "/api/filas/registros/",
  filaEspecialidades:
    process.env.NEXT_PUBLIC_FILA_ESPECIALIDADES_PATH ??
    "/api/filas/especialidades/",
  filaOpcoes:
    process.env.NEXT_PUBLIC_FILA_OPCOES_PATH ?? "/api/filas/opcoes/",
  pacientes:
    process.env.NEXT_PUBLIC_PACIENTES_PATH ?? "/api/pacientes/",

  cidadaoLogin:
    process.env.NEXT_PUBLIC_CIDADAO_LOGIN_PATH ?? "/api/auth/cidadao/login/",
  cidadaoRefresh:
    process.env.NEXT_PUBLIC_CIDADAO_REFRESH_PATH ??
    "/api/auth/cidadao/refresh/",
  cidadaoLogout:
    process.env.NEXT_PUBLIC_CIDADAO_LOGOUT_PATH ??
    "/api/auth/cidadao/logout/",
  cidadaoMe:
    process.env.NEXT_PUBLIC_CIDADAO_ME_PATH ?? "/api/auth/cidadao/me/",
  cidadaoFilas:
    process.env.NEXT_PUBLIC_CIDADAO_FILAS_PATH ?? "/api/cidadao/filas/",
};
