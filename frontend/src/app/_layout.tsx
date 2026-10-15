import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';

import { DebugBar } from '@/components/DebugBar';
import { MotorBadge } from '@/components/MotorBadge';
import { colores } from '@/components/ui';
import { ConfigProvider } from '@/lib/config';

export default function RootLayout() {
  return (
    <ConfigProvider>
      <StatusBar style="dark" />
      <View style={{ flex: 1, backgroundColor: colores.fondo }}>
        <Stack
          screenOptions={{
            headerRight: () => <MotorBadge />,
            headerTintColor: colores.primario,
            headerTitleStyle: { color: colores.texto },
            contentStyle: { backgroundColor: colores.fondo },
          }}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="lugar/[id]" options={{ title: 'Lugar' }} />
          <Stack.Screen name="lugar/form" options={{ title: 'Lugar' }} />
          <Stack.Screen name="checkin/form" options={{ title: 'Check-in' }} />
        </Stack>
        <DebugBar />
      </View>
    </ConfigProvider>
  );
}
