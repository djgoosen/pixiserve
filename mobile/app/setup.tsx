/**
 * Configure Pixiserve API base URL (required before Clerk sign-in).
 */

import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '../src/stores/authStore';

export default function SetupScreen() {
  const router = useRouter();
  const setServerUrl = useAuthStore((s) => s.setServerUrl);
  const existing = useAuthStore((s) => s.serverUrl);
  const [url, setUrl] = useState(existing ?? 'http://localhost:8000');

  const save = () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    setServerUrl(trimmed);
    router.replace('/login');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>Pixiserve server</Text>
        <Text style={styles.sub}>
          API base URL (no trailing slash). Use your machine LAN IP for a device simulator or phone,
          e.g. http://192.168.1.10:8000
        </Text>
        <TextInput
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          style={styles.input}
          placeholder="https://photos.example.com"
          placeholderTextColor="#6b7280"
        />
        <Pressable style={styles.btn} onPress={save}>
          <Text style={styles.btnText}>Continue</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  inner: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  title: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 8,
  },
  sub: {
    color: '#9ca3af',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#1a1a2e',
    borderRadius: 10,
    padding: 14,
    color: '#fff',
    fontSize: 16,
    marginBottom: 16,
  },
  btn: {
    backgroundColor: '#6366f1',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
