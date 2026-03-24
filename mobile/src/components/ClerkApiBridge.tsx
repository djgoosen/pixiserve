import { useEffect } from 'react';
import { useAuth, useClerk } from '@clerk/clerk-expo';
import { registerClerkApiBridge, unregisterClerkApiBridge } from '../services/clerkApiBridge';

/** Wires Clerk session into Axios interceptors (sync + uploads use the same client). */
export function ClerkApiBridge() {
  const { getToken } = useAuth();
  const { signOut } = useClerk();

  useEffect(() => {
    registerClerkApiBridge(
      () => getToken(),
      async () => {
        await signOut();
      }
    );
    return () => unregisterClerkApiBridge();
  }, [getToken, signOut]);

  return null;
}
