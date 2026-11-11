// Identifica el motor que respondio el ultimo pedido. Tocarlo lleva al selector de motor (Perfil).

import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { useConfig } from '@/lib/config';
import { colorMotor, colores, fuentes } from './ui';

export function MotorBadge() {
  const { historial, motor: elegido } = useConfig();
  const motor = historial[0]?.meta.motor;
  const color = motor ? colorMotor(motor) : colores.suave;
  return (
    <Pressable onPress={() => router.push('/ajustes')} style={{
      flexDirection: 'row', alignItems: 'center', gap: 6, marginRight: 16,
      backgroundColor: colores.blanco, borderWidth: 1.5, borderColor: elegido !== 'auto' ? color : colores.borde,
      borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5,
    }}>
      {elegido !== 'auto'
        ? <Ionicons name="lock-closed" size={10} color={color} />
        : <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: color }} />}
      <Text style={{ color, fontFamily: fuentes.extra, fontSize: 11, letterSpacing: 0.6 }}>
        {motor ? motor.toUpperCase() : 'AUTO'}
      </Text>
    </Pressable>
  );
}
