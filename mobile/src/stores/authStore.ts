/**
 * Non-auth app settings persisted locally (API base URL).
 * Session is handled by @clerk/clerk-expo (SecureStore token cache).
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

interface SettingsState {
  serverUrl: string | null;
  setServerUrl: (url: string) => void;
}

export const useAuthStore = create<SettingsState>()(
  persist(
    (set) => ({
      serverUrl: null,
      setServerUrl: (url: string) => {
        const normalized = url.replace(/\/$/, '');
        set({ serverUrl: normalized });
      },
    }),
    {
      name: 'pixiserve-mobile-settings',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ serverUrl: state.serverUrl }),
    }
  )
);
