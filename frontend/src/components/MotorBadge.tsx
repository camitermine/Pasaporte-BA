// Indicador del motor activo en el encabezado. Tocándolo se cambia de motor.

import { Pressable, Text } from 'react-native';

import { useConfig } from '@/lib/config';
import { colorMotor, colores } from './ui';

export function MotorBadge() {
  const { motor, cambiar } = useConfig();
  return (
    <Pressable
      onPress={() => cambiar({ motor: motor === 'mysql' ? 'hbase' : 'mysql' })}
      hitSlop={8}
      style={{ backgroundColor: colorMotor(motor), borderRadius: 999, paddingHorizontal: 12, paddingVertical: 5, marginRight: 12 }}>
      <Text style={{ color: colores.blanco, fontWeight: '800', fontSize: 12, letterSpacing: 0.5 }}>
        {motor === 'mysql' ? 'MySQL' : 'HBase'} ⇄
      </Text>
    </Pressable>
  );
}
