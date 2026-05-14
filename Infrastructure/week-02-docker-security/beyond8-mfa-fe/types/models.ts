export interface User {
  id: string;
  email: string;
  userNname: string;
  role: string[];
  isBlocked?: boolean;
  blockReason?: string | null;
  createdAt?: string;
}

export interface DecodedToken extends User {
  nbf?: number;
  exp?: number;
  iat?: number;
}
