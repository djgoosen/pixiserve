import { useEffect } from 'react'
import { useAuth, useClerk } from '@clerk/clerk-react'
import { setClerkGetToken, setClerkSignOut } from '@/api/authBridge'

/** Registers Clerk session helpers for Axios interceptors. */
export function ClerkTokenBridge() {
  const { getToken } = useAuth()
  const { signOut } = useClerk()

  useEffect(() => {
    setClerkGetToken(() => getToken())
    setClerkSignOut(async () => {
      await signOut()
      window.location.href = '/login'
    })
    return () => {
      setClerkGetToken(null)
      setClerkSignOut(null)
    }
  }, [getToken, signOut])

  return null
}
