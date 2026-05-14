import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { jwtDecode } from "jwt-decode";

export interface User {
  id: string;
  email: string;
  role: string[];
}

export interface DecodedToken extends User {
  nbf?: number;
  exp?: number;
  iat?: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export const decodeToken = (token: string): User | null => {
  try {
    const decoded = jwtDecode<Record<string, unknown>>(token);
    const id = (decoded.id || decoded.sub) as string | undefined;
    const email = decoded.email as string | undefined;
    if (!id || !email) return null;

    const rawRoles = Array.isArray(decoded.role)
      ? (decoded.role as string[])
      : decoded.role
        ? [decoded.role as string]
        : [];

    return {
      id,
      email,
      role: rawRoles.map((role) => role.toLowerCase()),
    };
  } catch {
    return null;
  }
};

export const decodeTokenWithExpiry = (token: string): DecodedToken | null => {
  try {
    const decoded = jwtDecode<Record<string, unknown>>(token);
    const id = (decoded.id || decoded.sub) as string | undefined;
    const email = decoded.email as string | undefined;
    if (!id || !email) return null;

    const rawRoles = Array.isArray(decoded.role)
      ? (decoded.role as string[])
      : decoded.role
        ? [decoded.role as string]
        : [];

    return {
      id,
      email,
      role: rawRoles.map((role) => role.toLowerCase()),
      nbf: decoded.nbf as number | undefined,
      exp: decoded.exp as number | undefined,
      iat: decoded.iat as number | undefined,
    };
  } catch {
    return null;
  }
};

const initialState: AuthState = {
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    dismissError(state) {
      state.error = null;
    },
    setTokens(
      state,
      action: PayloadAction<{ token: string; refreshToken?: string | null }>
    ) {
      const { token, refreshToken } = action.payload;
      const user = decodeToken(token);

      state.token = token;
      state.user = user;
      state.refreshToken = refreshToken ?? state.refreshToken;
      state.isAuthenticated = Boolean(user);
      state.error = null;
    },
    logout(state) {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.isAuthenticated = false;
      state.isLoading = false;
      state.error = null;
    },
  },
});

export const { setLoading, setError, dismissError, setTokens, logout } = authSlice.actions;
export default authSlice.reducer;
