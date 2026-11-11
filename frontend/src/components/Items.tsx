import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import type { Checkin, Lugar } from '@/lib/tipos';
import { colores, Estrellas, Etiqueta, formatearFecha, fuentes, IconoTipo, nombrePropio, s, tipoDe } from './ui';

export function ItemLugar({ lugar, extra, onPress }: { lugar: Lugar; extra?: string; onPress: () => void }) {
  const t = tipoDe(lugar.categoria.tipo);
  return (
    <Pressable onPress={onPress}
      style={({ pressed }) => [s.tarjeta, { flexDirection: 'row', gap: 14, padding: 10, opacity: pressed ? 0.85 : 1 }]}>
      <View>
        <IconoTipo tipo={lugar.categoria.tipo} tamanio={84} />
        <View style={{ position: 'absolute', top: 6, left: 6 }}>
          <Etiqueta texto={t.etiqueta} color={t.color} />
        </View>
      </View>
      <View style={{ flex: 1, paddingVertical: 4, justifyContent: 'space-between' }}>
        <View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
            <Ionicons name="location-outline" size={11} color={colores.suave} />
            <Text style={{ color: colores.suave, fontFamily: fuentes.medio, fontSize: 11, flex: 1 }} numberOfLines={1}>
              {lugar.barrio ? nombrePropio(lugar.barrio.nombre) : 'Barrio sin definir'}{extra ? ` · ${extra}` : ''}
            </Text>
          </View>
          <Text style={{ fontFamily: fuentes.titulo, color: colores.texto, fontSize: 18, lineHeight: 22, marginTop: 2 }} numberOfLines={2}>
            {nombrePropio(lugar.nombre)}
          </Text>
          <Text style={{ color: colores.suave, fontFamily: fuentes.medio, fontSize: 12 }} numberOfLines={1}>
            {nombrePropio(lugar.categoria.nombre)}
          </Text>
        </View>
        {lugar.barrio && (
          <Pressable
            onPress={() => router.push(`/checkin/form?idLugar=${lugar.id}`)}
            hitSlop={6}
            style={{
              alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 8,
              backgroundColor: colores.primarioClaro, borderRadius: 8, paddingHorizontal: 9, paddingVertical: 5,
            }}>
            <Ionicons name="checkmark" size={13} color={colores.primario} />
            <Text style={{ color: colores.primario, fontFamily: fuentes.negrita, fontSize: 11 }}>Hacer check-in</Text>
          </Pressable>
        )}
      </View>
    </Pressable>
  );
}

export function ItemCheckin({ checkin, mostrar, onPress }: {
  checkin: Checkin; mostrar: 'usuario' | 'lugar'; onPress?: () => void;
}) {
  const titulo = mostrar === 'usuario' ? `@${checkin.usuario.nombre}` : nombrePropio(checkin.lugar.nombre);
  return (
    <Pressable onPress={onPress} disabled={!onPress}
      style={({ pressed }) => [s.tarjeta, { flexDirection: 'row', gap: 12, opacity: pressed ? 0.85 : 1 }]}>
      <View style={{
        width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center',
        backgroundColor: mostrar === 'usuario' ? colores.acentoClaro : colores.primarioClaro,
      }}>
        {mostrar === 'usuario'
          ? <Text style={{ fontFamily: fuentes.extra, color: colores.acento, fontSize: 15 }}>{checkin.usuario.nombre.slice(0, 2).toUpperCase()}</Text>
          : <Ionicons name="checkmark-done" size={19} color={colores.primario} />}
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <Text style={{ fontFamily: fuentes.negrita, color: colores.texto, flex: 1, fontSize: 14 }} numberOfLines={1}>{titulo}</Text>
          <Estrellas valor={checkin.puntaje} tamanio={13} />
        </View>
        <Text style={[s.suave, { fontSize: 12 }]}>{formatearFecha(checkin.fecha_hora)}{onPress ? '  ·  tocá para editar' : ''}</Text>
        {checkin.comentario ? (
          <Text style={{ color: colores.texto, marginTop: 6, fontFamily: fuentes.regular, fontSize: 14, lineHeight: 20 }}>“{checkin.comentario}”</Text>
        ) : null}
      </View>
    </Pressable>
  );
}
