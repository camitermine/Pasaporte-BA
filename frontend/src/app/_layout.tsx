import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';

import { DebugBar } from '@/components/DebugBar';
import { MotorBadge } from '@/components/MotorBadge';
import { colores } from '@/components/ui';
import { ConfigProvider, useConfig } from '@/lib/config';

export default function RootLayout() {
  return (
    <ConfigProvider>
      <StatusBar style="dark" />
      <Navegacion />
    </ConfigProvider>
  );
}

function Navegacion() {
  const { token } = useConfig();
  return (
    <View style={{ flex: 1, backgroundColor: colores.fondo }}>
      <Stack screenOptions={{
        headerRight: () => <MotorBadge />,
        headerTintColor: colores.primario,
        headerTitleStyle: { color: colores.texto },
        contentStyle: { backgroundColor: colores.fondo },
      }}>
        <Stack.Protected guard={!!token}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="lugar/[id]" options={{ title: 'Lugar' }} />
          <Stack.Screen name="lugar/form" options={{ title: 'Lugar' }} />
          <Stack.Screen name="checkin/form" options={{ title: 'Check-in' }} />
          <Stack.Screen name="sugerencia/form" options={{ title: 'Sugerir lugar' }} />
          <Stack.Screen name="admin/sugerencias" options={{ title: 'Moderación' }} />
          <Stack.Screen name="favoritos" options={{ title: 'Mis favoritos' }} />
          <Stack.Screen name="sugerencias" options={{ title: 'Mis sugerencias' }} />
        </Stack.Protected>
        <Stack.Protected guard={!token}>
          <Stack.Screen name="login" options={{ title: 'Ingresar', headerShown: false }} />
        </Stack.Protected>
      </Stack>
      {!!token && <DebugBar />}
    </View>
  );
}
