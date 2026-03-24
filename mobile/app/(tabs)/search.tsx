import { StyleSheet, Text, View } from 'react-native';

export default function SearchPlaceholder() {
  return (
    <View style={styles.center}>
      <Text style={styles.text}>Search</Text>
      <Text style={styles.sub}>Coming soon</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  text: { color: '#fff', fontSize: 18, fontWeight: '600' },
  sub: { color: '#6b7280', marginTop: 8 },
});
