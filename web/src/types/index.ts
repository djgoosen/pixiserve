export interface User {
  id: string
  username: string
  email: string
  name: string | null
  is_admin: boolean
  created_at: string
}

export interface Asset {
  id: string
  owner_id: string
  file_hash_sha256: string
  original_filename: string | null
  storage_path: string
  thumb_path: string | null
  file_size_bytes: number
  mime_type: string
  asset_type: 'image' | 'video'
  width: number | null
  height: number | null
  captured_at: string | null
  latitude: number | null
  longitude: number | null
  city: string | null
  country: string | null
  is_favorite: boolean
  created_at: string
  updated_at: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface UploadResponse {
  asset: Asset
  is_duplicate: boolean
}
