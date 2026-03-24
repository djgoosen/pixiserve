/**
 * Settings tab - sync settings and account management.
 */

import { useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useClerk, useUser } from '@clerk/clerk-expo';
import { useAuthStore } from '../../src/stores/authStore';
import { useSyncStore, SyncStatus } from '../../src/stores/syncStore';
import { syncPhotos } from '../../src/services/syncService';

export default function SettingsScreen() {
  const { user } = useUser();
  const { signOut } = useClerk();
  const { serverUrl } = useAuthStore();
  const { status, progress, settings, lastSyncAt, updateSettings } = useSyncStore();
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await syncPhotos();
    } finally {
      setSyncing(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Sign out', 'Sign out of your account on this device?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: () => signOut(),
      },
    ]);
  };

  const statusColor = {
    idle: '#22c55e',
    scanning: '#eab308',
    syncing: '#3b82f6',
    paused: '#6b7280',
    error: '#ef4444',
  }[status];

  return (
    <ScrollView style={styles.container}>
      {/* Account Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Ionicons name="person" size={24} color="#6366f1" />
            <View style={styles.rowContent}>
              <Text style={styles.label}>
                {user?.username || user?.primaryEmailAddress?.emailAddress || 'Account'}
              </Text>
              <Text style={styles.sublabel}>
                {user?.primaryEmailAddress?.emailAddress ?? ''}
              </Text>
            </View>
          </View>
          <View style={styles.divider} />
          <View style={styles.row}>
            <Ionicons name="server" size={24} color="#6366f1" />
            <View style={styles.rowContent}>
              <Text style={styles.label}>Server</Text>
              <Text style={styles.sublabel}>{serverUrl}</Text>
            </View>
          </View>
        </View>
      </View>

      {/* Sync Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Backup & Sync</Text>
        <View style={styles.card}>
          {/* Sync Status */}
          <View style={styles.row}>
            <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
            <View style={styles.rowContent}>
              <Text style={styles.label}>
                {status === 'idle' && 'Backup complete'}
                {status === 'scanning' && 'Scanning photos...'}
                {status === 'syncing' && 'Uploading...'}
                {status === 'paused' && 'Paused'}
                {status === 'error' && 'Error'}
              </Text>
              {lastSyncAt && (
                <Text style={styles.sublabel}>
                  Last sync: {new Date(lastSyncAt).toLocaleString()}
                </Text>
              )}
            </View>
          </View>

          {/* Progress */}
          {(status === 'scanning' || status === 'syncing') && (
            <View style={styles.progressContainer}>
              <View style={styles.progressBar}>
                <View
                  style={[
                    styles.progressFill,
                    {
                      width: `${
                        progress.totalAssets > 0
                          ? (progress.syncedAssets / progress.totalAssets) * 100
                          : 0
                      }%`,
                    },
                  ]}
                />
              </View>
              <Text style={styles.progressText}>
                {progress.syncedAssets} / {progress.totalAssets}
              </Text>
            </View>
          )}

          <View style={styles.divider} />

          {/* Manual Sync Button */}
          <Pressable
            style={[styles.button, syncing && styles.buttonDisabled]}
            onPress={handleSync}
            disabled={syncing}
          >
            <Ionicons name="cloud-upload" size={20} color="#fff" />
            <Text style={styles.buttonText}>
              {syncing ? 'Syncing...' : 'Sync Now'}
            </Text>
          </Pressable>
        </View>
      </View>

      {/* Sync Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Sync Settings</Text>
        <View style={styles.card}>
          <View style={styles.settingRow}>
            <View>
              <Text style={styles.label}>Auto Sync</Text>
              <Text style={styles.sublabel}>Automatically back up new photos</Text>
            </View>
            <Switch
              value={settings.autoSync}
              onValueChange={(value) => updateSettings({ autoSync: value })}
              trackColor={{ false: '#374151', true: '#6366f1' }}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingRow}>
            <View>
              <Text style={styles.label}>WiFi Only</Text>
              <Text style={styles.sublabel}>Only sync when connected to WiFi</Text>
            </View>
            <Switch
              value={settings.syncOnWifiOnly}
              onValueChange={(value) => updateSettings({ syncOnWifiOnly: value })}
              trackColor={{ false: '#374151', true: '#6366f1' }}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingRow}>
            <View>
              <Text style={styles.label}>Sync Videos</Text>
              <Text style={styles.sublabel}>Include videos in backup</Text>
            </View>
            <Switch
              value={settings.syncVideos}
              onValueChange={(value) => updateSettings({ syncVideos: value })}
              trackColor={{ false: '#374151', true: '#6366f1' }}
            />
          </View>
        </View>
      </View>

      {/* Sign out (Clerk) */}
      <View style={styles.section}>
        <Pressable style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out" size={20} color="#ef4444" />
          <Text style={styles.logoutText}>Sign out</Text>
        </Pressable>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Pixiserve v0.1.0</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    padding: 16,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  rowContent: {
    flex: 1,
  },
  label: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  sublabel: {
    color: '#6b7280',
    fontSize: 13,
    marginTop: 2,
  },
  divider: {
    height: 1,
    backgroundColor: '#2d2d44',
    marginVertical: 12,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  progressContainer: {
    marginTop: 12,
  },
  progressBar: {
    height: 4,
    backgroundColor: '#2d2d44',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#6366f1',
  },
  progressText: {
    color: '#6b7280',
    fontSize: 12,
    marginTop: 4,
    textAlign: 'right',
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#6366f1',
    padding: 12,
    borderRadius: 8,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#1a1a2e',
    padding: 16,
    borderRadius: 12,
  },
  logoutText: {
    color: '#ef4444',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    padding: 32,
    alignItems: 'center',
  },
  footerText: {
    color: '#4b5563',
    fontSize: 12,
  },
});
