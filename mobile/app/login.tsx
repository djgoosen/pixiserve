/**
 * Clerk sign-in: Google and Apple OAuth (enable providers in Clerk dashboard).
 */

import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSSO } from '@clerk/clerk-expo';
import { useAuthStore } from '../src/stores/authStore';

WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
  const router = useRouter();
  const serverUrl = useAuthStore((s) => s.serverUrl);
  const { startSSOFlow } = useSSO();
  const [busy, setBusy] = useState<'google' | 'apple' | null>(null);

  const redirectUrl = Linking.createURL('oauth-native', { scheme: 'pixiserve' });

  const runOAuth = async (strategy: 'oauth_google' | 'oauth_apple') => {
    setBusy(strategy === 'oauth_google' ? 'google' : 'apple');
    try {
      const { createdSessionId, setActive } = await startSSOFlow({
        strategy,
        redirectUrl,
      });
      if (createdSessionId && setActive) {
        await setActive({ session: createdSessionId });
        router.replace('/(tabs)');
      }
    } catch (e) {
      console.warn('OAuth error', e);
    } finally {
      setBusy(null);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sign in</Text>
      <Text style={styles.sub}>Server: {serverUrl ?? '—'}</Text>

      <Pressable
        style={[styles.btn, busy && styles.btnDisabled]}
        onPress={() => runOAuth('oauth_google')}
        disabled={!!busy}
      >
        {busy === 'google' ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnText}>Continue with Google</Text>
        )}
      </Pressable>

      {Platform.OS === 'ios' && (
        <Pressable
          style={[styles.btn, busy && styles.btnDisabled]}
          onPress={() => runOAuth('oauth_apple')}
          disabled={!!busy}
        >
          {busy === 'apple' ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnText}>Continue with Apple</Text>
          )}
        </Pressable>
      )}

      <Pressable style={styles.linkWrap} onPress={() => router.push('/setup')}>
        <Text style={styles.link}>Change server URL</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    padding: 24,
    justifyContent: 'center',
  },
  title: {
    color: '#fff',
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
  },
  sub: {
    color: '#6b7280',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 32,
  },
  btn: {
    backgroundColor: '#6366f1',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 12,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  linkWrap: {
    marginTop: 24,
    alignItems: 'center',
  },
  link: {
    color: '#818cf8',
    fontSize: 15,
  },
});
