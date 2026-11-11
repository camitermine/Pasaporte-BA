import { DMSerifDisplay_400Regular, DMSerifDisplay_400Regular_Italic } from '@expo-google-fonts/dm-serif-display';
import {
  Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold, useFonts,
} from '@expo-google-fonts/manrope';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform, View } from 'react-native';

import { DebugBar } from '@/components/DebugBar';
import { MotorBadge } from '@/components/MotorBadge';
import { colores, fuentes } from '@/components/ui';
import { ConfigProvider, useConfig } from '@/lib/config';

export default function RootLayout() {
  const [fuentesListas] = useFonts({
    DMSerifDisplay_400Regular, DMSerifDisplay_400Regular_Italic,
    Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold,
  });
  if (!fuentesListas) return null;

  return (
    <ConfigProvider>
      <StatusBar style="dark" />
      <MarcoWeb>
        <Navegacion />
      </MarcoWeb>
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
        headerTitleStyle: { color: colores.texto, fontFamily: fuentes.titulo, fontSize: 21 },
        headerStyle: { backgroundColor: colores.fondo },
        headerShadowVisible: false,
        headerBackButtonDisplayMode: 'minimal',
        contentStyle: { backgroundColor: colores.fondo },
      }}>
        <Stack.Protected guard={!!token}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="lugar/[id]" options={{ title: '', headerTransparent: true }} />
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

/** En web (presentación por pantalla compartida) mostramos la app centrada con ancho de celular. */
function MarcoWeb({ children }: { children: React.ReactNode }) {
  if (Platform.OS !== 'web') return <>{children}</>;
  return (
    <View style={{ flex: 1, backgroundColor: '#D9E5DF', alignItems: 'center' }}>
      <View style={{
        flex: 1, width: '100%', maxWidth: 440, backgroundColor: colores.fondo, overflow: 'hidden',
        boxShadow: '0 0 70px rgba(36,65,51,0.18)',
      }}>
        {children}
      </View>
    </View>
  );
}
