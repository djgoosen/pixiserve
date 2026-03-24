/**
 * Single asset detail (minimal stub; expand with viewer later).
 */

import { Stack, useLocalSearchParams } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

export default function AssetDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  return (
    <>
      <Stack.Screen options={{ title: 'Photo' }} />
      <View style={styles.container}>
        <Text style={styles.text}>Asset {id}</Text>
        <Text style={styles.sub}>Full viewer coming soon</Text>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  text: { color: '#fff', fontSize: 18, fontWeight: '600' },
  sub: { color: '#6b7280', marginTop: 8 },
});
