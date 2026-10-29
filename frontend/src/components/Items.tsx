import { Pressable, Text, View } from 'react-native';

import type { Checkin, Lugar } from '@/lib/tipos';
import { colores, Estrellas, formatearFecha, s } from './ui';

const ICONO_TIPO: Record<string, string> = { gastronomia: '☕', cultura: '🎭', patrimonio: '🗿' };

export function ItemLugar({ lugar, extra, onPress }: { lugar: Lugar; extra?: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.tarjeta, { flexDirection: 'row', gap: 12, opacity: pressed ? 0.7 : 1 }]}>
      <Text style={{ fontSize: 26 }}>{ICONO_TIPO[lugar.categoria.tipo] ?? '📍'}</Text>
      <View style={{ flex: 1 }}>
        <Text style={{ fontWeight: '700', color: colores.texto, fontSize: 15 }} numberOfLines={1}>{lugar.nombre}</Text>
        <Text style={s.suave} numberOfLines={1}>
          {lugar.categoria.nombre} · {lugar.barrio?.nombre ?? 'Barrio sin definir'}
        </Text>
        {lugar.direccion ? <Text style={s.suave} numberOfLines={1}>{lugar.direccion}</Text> : null}
      </View>
      {extra ? <Text style={{ color: colores.primario, fontWeight: '700' }}>{extra}</Text> : null}
    </Pressable>
  );
}

export function ItemCheckin({ checkin, mostrar, onPress }: {
  checkin: Checkin; mostrar: 'usuario' | 'lugar'; onPress?: () => void;
}) {
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={({ pressed }) => [s.tarjeta, { opacity: pressed ? 0.7 : 1 }]}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ fontWeight: '700', color: colores.texto, flex: 1 }} numberOfLines={1}>
          {mostrar === 'usuario' ? `@${checkin.usuario.nombre}` : checkin.lugar.nombre}
        </Text>
        <Estrellas valor={checkin.puntaje} tamanio={14} />
      </View>
      <Text style={s.suave}>{formatearFecha(checkin.fecha_hora)}{onPress ? '  ·  tocá para editar' : ''}</Text>
      {checkin.comentario ? <Text style={{ color: colores.texto, marginTop: 4 }}>“{checkin.comentario}”</Text> : null}
    </Pressable>
  );
}
