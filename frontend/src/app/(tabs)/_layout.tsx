import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router';
import { ComponentProps } from 'react';
import type { ColorValue } from 'react-native';

import { MotorBadge } from '@/components/MotorBadge';
import { colores } from '@/components/ui';

type Icono = ComponentProps<typeof Ionicons>['name'];

const icono = (nombre: Icono) => {
  const IconoTab = ({ color, size }: { color: ColorValue; size: number }) => (
    <Ionicons name={nombre} color={color as string} size={size} />
  );
  IconoTab.displayName = `IconoTab(${nombre})`;
  return IconoTab;
};

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colores.primario,
        headerRight: () => <MotorBadge />,
        headerTitleStyle: { color: colores.texto },
        sceneStyle: { backgroundColor: colores.fondo },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Explorar', tabBarIcon: icono('search') }} />
      <Tabs.Screen name="cerca" options={{ title: 'Cerca', tabBarIcon: icono('navigate') }} />
      <Tabs.Screen name="pasaporte" options={{ title: 'Pasaporte', tabBarIcon: icono('ribbon') }} />
      <Tabs.Screen name="ranking" options={{ title: 'Ranking', tabBarIcon: icono('trophy') }} />
      <Tabs.Screen name="ajustes" options={{ title: 'Ajustes', tabBarIcon: icono('settings') }} />
    </Tabs>
  );
}
