/**
 * Background sync service for photo backup.
 *
 * Flow:
 * 1. Scan local media library
 * 2. Compute SHA256 hashes
 * 3. Check with server which files are new
 * 4. Upload new files
 * 5. Update sync cursor
 */

import * as FileSystem from 'expo-file-system';
import * as MediaLibrary from 'expo-media-library';
import * as Crypto from 'expo-crypto';
import NetInfo from '@react-native-community/netinfo';
import { api } from './api';
import { useSyncStore } from '../stores/syncStore';

// Batch size for hash checking
const BATCH_SIZE = 100;

// Concurrent uploads
const CONCURRENT_UPLOADS = 3;

/**
 * Compute SHA256 hash of a file.
 */
async function computeFileHash(uri: string): Promise<string> {
  // Read file as base64 and compute hash
  // Note: For large files, this should be done in chunks
  const fileInfo = await FileSystem.getInfoAsync(uri);
  if (!fileInfo.exists) {
    throw new Error('File not found');
  }

  const content = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });

  return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, content);
}

/**
 * Get all photos from the device.
 */
async function getAllMedia(): Promise<MediaLibrary.Asset[]> {
  const { status } = await MediaLibrary.requestPermissionsAsync();
  if (status !== 'granted') {
    throw new Error('Media library permission denied');
  }

  const assets: MediaLibrary.Asset[] = [];
  let hasMore = true;
  let endCursor: string | undefined;

  while (hasMore) {
    const page = await MediaLibrary.getAssetsAsync({
      first: 100,
      after: endCursor,
      mediaType: [MediaLibrary.MediaType.photo, MediaLibrary.MediaType.video],
      sortBy: [MediaLibrary.SortBy.creationTime],
    });

    assets.push(...page.assets);
    hasMore = page.hasNextPage;
    endCursor = page.endCursor;
  }

  return assets;
}

/**
 * Sync photos to server.
 */
export async function syncPhotos(): Promise<void> {
  const store = useSyncStore.getState();
  const { settings } = store;

  // Check network
  const netInfo = await NetInfo.fetch();
  if (!netInfo.isConnected) {
    store.setError('No network connection');
    return;
  }

  if (settings.syncOnWifiOnly && netInfo.type !== 'wifi') {
    store.setError('Waiting for WiFi connection');
    return;
  }

  try {
    store.setStatus('scanning');
    store.setError(null);

    // Get all media
    const allMedia = await getAllMedia();

    // Filter based on settings
    let mediaToSync = allMedia;
    if (!settings.syncVideos) {
      mediaToSync = mediaToSync.filter((a) => a.mediaType !== 'video');
    }

    store.setProgress({
      totalAssets: mediaToSync.length,
      pendingAssets: mediaToSync.length,
    });

    // Compute hashes in batches
    const hashMap: Map<string, MediaLibrary.Asset> = new Map();

    for (let i = 0; i < mediaToSync.length; i += BATCH_SIZE) {
      const batch = mediaToSync.slice(i, i + BATCH_SIZE);

      for (const asset of batch) {
        try {
          const assetInfo = await MediaLibrary.getAssetInfoAsync(asset);
          if (assetInfo.localUri) {
            const hash = await computeFileHash(assetInfo.localUri);
            hashMap.set(hash, asset);
          }
        } catch (error) {
          console.warn(`Failed to hash ${asset.filename}:`, error);
        }
      }

      // Update progress
      store.setProgress({
        syncedAssets: Math.min(i + BATCH_SIZE, mediaToSync.length),
      });
    }

    // Check which hashes are new
    store.setStatus('syncing');
    const hashes = Array.from(hashMap.keys());

    const checkResult = await api.post<{
      existing: string[];
      missing: string[];
    }>('/sync/check', { hashes });

    const missingHashes = checkResult.data.missing;
    store.setProgress({
      pendingAssets: missingHashes.length,
      syncedAssets: hashes.length - missingHashes.length,
    });

    if (missingHashes.length === 0) {
      store.setStatus('idle');
      store.setSyncCursor(new Date().toISOString());
      return;
    }

    // Upload missing files
    const uploadQueue = missingHashes.map((hash) => ({
      hash,
      asset: hashMap.get(hash)!,
    }));

    // Process uploads with concurrency limit
    let uploadedCount = 0;
    for (let i = 0; i < uploadQueue.length; i += CONCURRENT_UPLOADS) {
      const batch = uploadQueue.slice(i, i + CONCURRENT_UPLOADS);

      await Promise.all(
        batch.map(async ({ hash, asset }) => {
          try {
            store.setProgress({ currentAsset: asset.filename });

            const assetInfo = await MediaLibrary.getAssetInfoAsync(asset);
            if (!assetInfo.localUri) return;

            // Create form data for upload
            const formData = new FormData();
            formData.append('file', {
              uri: assetInfo.localUri,
              name: asset.filename,
              type: asset.mediaType === 'video' ? 'video/mp4' : 'image/jpeg',
            } as any);

            await api.post('/assets', formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });

            uploadedCount++;
            store.setProgress({
              syncedAssets: hashes.length - missingHashes.length + uploadedCount,
              pendingAssets: missingHashes.length - uploadedCount,
            });
          } catch (error) {
            console.error(`Failed to upload ${asset.filename}:`, error);
          }
        })
      );
    }

    // Update cursor
    store.setSyncCursor(new Date().toISOString());
    store.setStatus('idle');
    store.setProgress({ currentAsset: null });
  } catch (error) {
    console.error('Sync failed:', error);
    store.setError(error instanceof Error ? error.message : 'Sync failed');
  }
}

/**
 * Register device with server.
 */
export async function registerDevice(): Promise<string> {
  const deviceInfo = {
    device_name: 'Mobile Device', // Should get actual device name
    device_type: 'android', // Should detect platform
    device_id: 'unique-device-id', // Should use actual device ID
    app_version: '0.1.0',
  };

  const result = await api.post<{ id: string }>('/sync/devices', deviceInfo);
  return result.data.id;
}
