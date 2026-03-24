/** Bridges @clerk/clerk-react into the Axios stack (outside React tree). */

export type ClerkGetToken = () => Promise<string | null>

let getTokenFn: ClerkGetToken | null = null
let signOutFn: (() => void | Promise<void>) | null = null

export function setClerkGetToken(fn: ClerkGetToken | null): void {
  getTokenFn = fn
}

export function setClerkSignOut(fn: (() => void | Promise<void>) | null): void {
  signOutFn = fn
}

export async function getClerkTokenForApi(): Promise<string | null> {
  if (!getTokenFn) return null
  return getTokenFn()
}

export async function clerkSignOutAndRedirect(): Promise<void> {
  if (signOutFn) {
    await signOutFn()
  }
  window.location.href = '/login'
}
