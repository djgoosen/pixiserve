import { useState } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { format } from 'date-fns'
import {
  ChevronLeft,
  ChevronRight,
  Heart,
  Trash2,
  Download,
  Info,
  X,
  MapPin,
  Calendar,
  HardDrive,
} from 'lucide-react'
import { Modal, Button } from '@/components/ui'
import { useGalleryStore } from '@/stores/galleryStore'
import { getAssetFileUrl, toggleFavorite, deleteAsset } from '@/api/assets'
import { useMediaUrl } from '@/hooks/useMediaUrl'
import type { Asset } from '@/types'

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

export function PhotoViewer() {
  const { viewerOpen, selectedAsset, closeViewer, assets, updateAsset, removeAsset } =
    useGalleryStore()
  const { getToken } = useAuth()
  const imageUrl = useMediaUrl(selectedAsset?.id ?? null)
  const [showInfo, setShowInfo] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!selectedAsset) return null

  const currentIndex = assets.findIndex((a) => a.id === selectedAsset.id)
  const hasPrev = currentIndex > 0
  const hasNext = currentIndex < assets.length - 1

  const goToPrev = () => {
    if (hasPrev) {
      useGalleryStore.getState().setSelectedAsset(assets[currentIndex - 1])
    }
  }

  const goToNext = () => {
    if (hasNext) {
      useGalleryStore.getState().setSelectedAsset(assets[currentIndex + 1])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') goToPrev()
    if (e.key === 'ArrowRight') goToNext()
  }

  const handleToggleFavorite = async () => {
    setLoading(true)
    try {
      const updated = await toggleFavorite(selectedAsset.id)
      updateAsset(selectedAsset.id, { is_favorite: updated.is_favorite })
    } catch (error) {
      console.error('Failed to toggle favorite:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this photo?')) return

    setLoading(true)
    try {
      await deleteAsset(selectedAsset.id)
      removeAsset(selectedAsset.id)
    } catch (error) {
      console.error('Failed to delete:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    const t = await getToken()
    if (!t) return
    const url = `${getAssetFileUrl(selectedAsset.id)}?token=${encodeURIComponent(t)}`
    const link = document.createElement('a')
    link.href = url
    link.download = selectedAsset.original_filename || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Modal
      isOpen={viewerOpen}
      onClose={closeViewer}
      className="w-full h-full flex items-center justify-center"
      showCloseButton={false}
    >
      <div
        className="relative w-full h-full flex flex-col"
        onKeyDown={handleKeyDown}
        tabIndex={0}
      >
        {/* Top toolbar */}
        <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-4 bg-gradient-to-b from-black/50 to-transparent">
          <button
            onClick={closeViewer}
            className="p-2 text-white/80 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleToggleFavorite}
              disabled={loading}
              className="text-white hover:bg-white/20"
            >
              <Heart
                className={`w-5 h-5 ${selectedAsset.is_favorite ? 'fill-red-500 text-red-500' : ''}`}
              />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowInfo(!showInfo)}
              className="text-white hover:bg-white/20"
            >
              <Info className="w-5 h-5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              className="text-white hover:bg-white/20"
            >
              <Download className="w-5 h-5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={loading}
              className="text-white hover:bg-white/20"
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Main image */}
        <div className="flex-1 flex items-center justify-center p-4">
          {!imageUrl ? (
            <p className="text-white/80">Loading…</p>
          ) : selectedAsset.asset_type === 'video' ? (
            <video
              src={imageUrl}
              controls
              className="max-w-full max-h-full object-contain"
            />
          ) : (
            <img
              src={imageUrl}
              alt={selectedAsset.original_filename || 'Photo'}
              className="max-w-full max-h-full object-contain"
            />
          )}
        </div>

        {/* Navigation arrows */}
        {hasPrev && (
          <button
            onClick={goToPrev}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
          >
            <ChevronLeft className="w-8 h-8" />
          </button>
        )}
        {hasNext && (
          <button
            onClick={goToNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
          >
            <ChevronRight className="w-8 h-8" />
          </button>
        )}

        {/* Info panel */}
        {showInfo && (
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-white shadow-xl p-6 overflow-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Details</h3>
              <button onClick={() => setShowInfo(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {selectedAsset.original_filename && (
                <div>
                  <p className="text-sm text-gray-500">Filename</p>
                  <p className="font-medium truncate">{selectedAsset.original_filename}</p>
                </div>
              )}

              {selectedAsset.captured_at && (
                <div className="flex items-start gap-3">
                  <Calendar className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-sm text-gray-500">Date taken</p>
                    <p className="font-medium">
                      {format(new Date(selectedAsset.captured_at), 'PPP p')}
                    </p>
                  </div>
                </div>
              )}

              {(selectedAsset.city || selectedAsset.country) && (
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-sm text-gray-500">Location</p>
                    <p className="font-medium">
                      {[selectedAsset.city, selectedAsset.country].filter(Boolean).join(', ')}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-3">
                <HardDrive className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-500">File size</p>
                  <p className="font-medium">{formatFileSize(selectedAsset.file_size_bytes)}</p>
                </div>
              </div>

              {selectedAsset.width && selectedAsset.height && (
                <div>
                  <p className="text-sm text-gray-500">Dimensions</p>
                  <p className="font-medium">
                    {selectedAsset.width} x {selectedAsset.height}
                  </p>
                </div>
              )}

              <div>
                <p className="text-sm text-gray-500">Type</p>
                <p className="font-medium">{selectedAsset.mime_type}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
