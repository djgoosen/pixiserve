import { useState } from 'react'
import { Heart, Play } from 'lucide-react'
import { clsx } from 'clsx'
import type { Asset } from '@/types'
import { useMediaUrl } from '@/hooks/useMediaUrl'

interface PhotoCardProps {
  asset: Asset
  onClick: () => void
  isSelected?: boolean
  onSelect?: () => void
}

export function PhotoCard({ asset, onClick, isSelected, onSelect }: PhotoCardProps) {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  const imageUrl = useMediaUrl(asset.id)

  return (
    <div
      className={clsx(
        'relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer group',
        isSelected && 'ring-2 ring-primary-500 ring-offset-2'
      )}
      onClick={onClick}
    >
      {!error && imageUrl ? (
        <img
          src={imageUrl}
          alt={asset.original_filename || 'Photo'}
          className={clsx(
            'w-full h-full object-cover transition-opacity duration-300',
            loaded ? 'opacity-100' : 'opacity-0'
          )}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
          loading="lazy"
        />
      ) : !imageUrl && !error ? (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          <span className="text-sm">Loading…</span>
        </div>
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          <span className="text-sm">Failed to load</span>
        </div>
      )}

      {!loaded && !error && imageUrl && (
        <div className="absolute inset-0 bg-gray-200 animate-pulse" />
      )}

      {/* Overlay on hover */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />

      {/* Video indicator */}
      {asset.asset_type === 'video' && (
        <div className="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full text-white">
          <Play className="w-4 h-4" fill="currentColor" />
        </div>
      )}

      {/* Favorite indicator */}
      {asset.is_favorite && (
        <div className="absolute top-2 left-2">
          <Heart className="w-5 h-5 text-red-500" fill="currentColor" />
        </div>
      )}

      {/* Selection checkbox */}
      {onSelect && (
        <div
          className={clsx(
            'absolute top-2 left-2 w-6 h-6 rounded-full border-2 transition-all',
            isSelected
              ? 'bg-primary-500 border-primary-500'
              : 'bg-white/80 border-white group-hover:border-gray-300'
          )}
          onClick={(e) => {
            e.stopPropagation()
            onSelect()
          }}
        >
          {isSelected && (
            <svg className="w-full h-full text-white p-1" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"
              />
            </svg>
          )}
        </div>
      )}
    </div>
  )
}
