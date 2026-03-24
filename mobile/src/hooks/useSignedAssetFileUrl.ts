import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-expo';
import { useAuthStore } from '../stores/authStore';

/** URL for GET /assets/{id}/file with Clerk JWT in `token` (for React Native Image). */
export function useSignedAssetFileUrl(assetId: string | null): string | null {
  const { getToken, isSignedIn } = useAuth();
  const serverUrl = useAuthStore((s) => s.serverUrl);
  const [uri, setUri] = useState<string | null>(null);

  useEffect(() => {
    if (!assetId || !isSignedIn || !serverUrl) {
      setUri(null);
      return;
    }
    let cancelled = false;
    (async () => {
      const t = await getToken();
      if (cancelled || !t) return;
      const base = `${serverUrl}/api/v1`;
      setUri(`${base}/assets/${assetId}/file?token=${encodeURIComponent(t)}`);
    })();
    return () => {
      cancelled = true;
    };
  }, [assetId, isSignedIn, serverUrl, getToken]);

  return uri;
}
