export const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const API_URL = `${API_BASE_URL}/api`;

export const TOKEN_STORAGE_KEY = "ck_token";
export const USER_STORAGE_KEY = "ck_user";
