/**
 * Entry redirect: server URL → Clerk sign-in → main tabs.
 */

import { Redirect } from 'expo-router';
import { useAuth } from '@clerk/clerk-expo';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { useAuthStore } from '../src/stores/authStore';

export default function Index() {
  const { isLoaded, isSignedIn } = useAuth();
  const serverUrl = useAuthStore((s) => s.serverUrl);

  if (!isLoaded) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  if (!serverUrl) {
    return <Redirect href="/setup" />;
  }
  if (!isSignedIn) {
    return <Redirect href="/login" />;
  }
  return <Redirect href="/(tabs)" />;
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f0f1a',
  },
});
