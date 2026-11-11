import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router';
import { ComponentProps } from 'react';
import { type ColorValue, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Marca } from '@/components/Marca';
import { MotorBadge } from '@/components/MotorBadge';
import { colores, fuentes } from '@/components/ui';

type Icono = ComponentProps<typeof Ionicons>['name'];

const icono = (nombre: Icono, activo: Icono) => {
  const IconoTab = ({ color, focused }: { color: ColorValue; focused: boolean }) => (
    <View style={{
      width: 44, height: 28, borderRadius: 10, alignItems: 'center', justifyContent: 'center',
      backgroundColor: focused ? colores.primarioClaro : 'transparent',
    }}>
      <Ionicons name={focused ? activo : nombre} color={color as string} size={20} />
    </View>
  );
  IconoTab.displayName = `IconoTab(${nombre})`;
  return IconoTab;
};

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colores.primario,
        tabBarInactiveTintColor: colores.suave,
        tabBarLabelStyle: { fontFamily: fuentes.negrita, fontSize: 10.5, marginTop: 2 },
        tabBarStyle: {
          backgroundColor: colores.blanco, borderTopColor: colores.borde,
          height: 70 + insets.bottom, paddingTop: 6, paddingBottom: insets.bottom + 10,
        },
        headerRight: () => <MotorBadge />,
        headerStyle: { backgroundColor: colores.fondo },
        headerShadowVisible: false,
        headerTitleStyle: { color: colores.texto, fontFamily: fuentes.titulo, fontSize: 24 },
        headerTitleAlign: 'left',
        sceneStyle: { backgroundColor: colores.fondo },
      }}>
      <Tabs.Screen name="index" options={{
        title: 'Inicio', headerTitle: () => null, headerLeft: () => <Marca />, tabBarIcon: icono('home-outline', 'home'),
      }} />
      <Tabs.Screen name="cerca" options={{ title: 'Cerca', headerTitle: 'Cerca tuyo', tabBarIcon: icono('map-outline', 'map') }} />
      <Tabs.Screen name="pasaporte" options={{ title: 'Pasaporte', headerTitle: 'Mi pasaporte', tabBarIcon: icono('ribbon-outline', 'ribbon') }} />
      <Tabs.Screen name="ranking" options={{ title: 'Ranking', headerTitle: 'Ranking del mes', tabBarIcon: icono('trophy-outline', 'trophy') }} />
      <Tabs.Screen name="ajustes" options={{ title: 'Perfil', headerTitle: 'Perfil', tabBarIcon: icono('person-outline', 'person') }} />
    </Tabs>
  );
}
