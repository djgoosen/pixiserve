import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { getAssetFileUrl } from '@/api/assets'

/** Signed URL for asset file stream (query token; see API MediaUser). */
export function useMediaUrl(assetId: string | null): string | null {
  const { isSignedIn, getToken } = useAuth()
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!assetId || !isSignedIn) {
      setUrl(null)
      return
    }
    let cancelled = false
    ;(async () => {
      const t = await getToken()
      if (cancelled || !t) return
      setUrl(`${getAssetFileUrl(assetId)}?token=${encodeURIComponent(t)}`)
    })()
    return () => {
      cancelled = true
    }
  }, [assetId, isSignedIn, getToken])

  return url
}
