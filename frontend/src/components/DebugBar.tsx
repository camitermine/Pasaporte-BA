// Panel de debug: muestra qué operaciones ejecutó el backend contra la base en la última request.

import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useConfig } from '@/lib/config';
import { colorMotor, colores, mono } from './ui';

export function DebugBar() {
  const { debug, historial } = useConfig();
  const [abierto, setAbierto] = useState(false);
  const [indice, setIndice] = useState(0);
  const insets = useSafeAreaInsets();
  if (!debug || historial.length === 0) return null;

  const registro = historial[Math.min(indice, historial.length - 1)];
  const { meta } = registro;

  return (
    <View style={{ backgroundColor: '#0B1220', paddingBottom: insets.bottom }}>
      <Pressable
        onPress={() => {
          setAbierto(!abierto);
          setIndice(0);
        }}
        style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, gap: 8 }}>
        <View style={{ backgroundColor: colorMotor(meta.motor), borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 }}>
          <Text style={{ color: colores.blanco, fontSize: 11, fontWeight: '800' }}>{meta.motor.toUpperCase()}</Text>
        </View>
        <Text style={{ color: '#CBD5E1', fontFamily: mono, fontSize: 11, flex: 1 }} numberOfLines={1}>
          {registro.pedido}
        </Text>
        <Text style={{ color: '#94A3B8', fontFamily: mono, fontSize: 11 }}>
          {meta.duracion_ms} ms · {meta.operaciones.length} op
        </Text>
        <Text style={{ color: '#94A3B8' }}>{abierto ? '▾' : '▴'}</Text>
      </Pressable>

      {abierto && (
        <View style={{ maxHeight: 280, borderTopWidth: 1, borderTopColor: '#1E293B' }}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ paddingHorizontal: 8, paddingVertical: 6, flexGrow: 0 }}>
            {historial.map((h, i) => (
              <Pressable key={i} onPress={() => setIndice(i)}
                style={{ paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, marginRight: 6,
                  backgroundColor: i === indice ? '#1E293B' : 'transparent' }}>
                <Text style={{ color: i === indice ? '#F8FAFC' : '#64748B', fontFamily: mono, fontSize: 10 }}>
                  {h.pedido.split('?')[0]}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
          <ScrollView style={{ paddingHorizontal: 12 }} contentContainerStyle={{ paddingBottom: 10 }}>
            {meta.operaciones.map((op, i) => (
              <View key={i} style={{ marginBottom: 8 }}>
                <Text style={{ color: '#E2E8F0', fontFamily: mono, fontSize: 11 }} selectable>{op.op}</Text>
                <Text style={{ color: '#64748B', fontFamily: mono, fontSize: 10 }}>{op.ms} ms</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}
    </View>
  );
}
