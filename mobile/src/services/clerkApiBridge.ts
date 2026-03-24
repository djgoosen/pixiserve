/**
 * Connects @clerk/clerk-expo session to the Axios client (non-React callers).
 */

export type TokenGetter = () => Promise<string | null>;
export type SignOutFn = () => Promise<void>;

let getTokenFn: TokenGetter | null = null;
let signOutFn: SignOutFn | null = null;

export function registerClerkApiBridge(getToken: TokenGetter, signOut: SignOutFn): void {
  getTokenFn = getToken;
  signOutFn = signOut;
}

export function unregisterClerkApiBridge(): void {
  getTokenFn = null;
  signOutFn = null;
}

export async function getClerkTokenForApi(): Promise<string | null> {
  if (!getTokenFn) return null;
  return getTokenFn();
}

export async function signOutViaApiBridge(): Promise<void> {
  if (signOutFn) {
    await signOutFn();
  }
}
