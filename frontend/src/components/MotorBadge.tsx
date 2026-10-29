// Identifica el motor que respondio el ultimo pedido. No es un selector.

import { Text, View } from 'react-native';

import { useConfig } from '@/lib/config';
import { colorMotor, colores } from './ui';

export function MotorBadge() {
  const { historial } = useConfig();
  const motor = historial[0]?.meta.motor;
  return (
    <View style={{
      backgroundColor: motor ? colorMotor(motor) : colores.suave,
      borderRadius: 999, paddingHorizontal: 12, paddingVertical: 5, marginRight: 12,
    }}>
      <Text style={{ color: colores.blanco, fontWeight: '800', fontSize: 12, letterSpacing: 0.5 }}>
        {motor ? motor.toUpperCase() : 'AUTO'}
      </Text>
    </View>
  );
}
