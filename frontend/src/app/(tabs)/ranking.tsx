// Ranking mensual de lugares más visitados de un barrio (consulta compleja).

import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';

import { Selector } from '@/components/Selector';
import { colores, Estado, fuentes, nombrePropio, s } from '@/components/ui';
import { qs, useApi, useCarga } from '@/lib/api';
import type { Barrio, ItemRanking } from '@/lib/tipos';

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const MEDALLAS = ['#E3A92B', '#9AA5A0', '#B5652B'];

export default function Ranking() {
  const api = useApi();
  const hoy = new Date();
  const [anio, setAnio] = useState(hoy.getFullYear());
  const [mes, setMes] = useState(hoy.getMonth() + 1);
  const [barrio, setBarrio] = useState<number | null>(null);

  const barrios = useCarga(() => api.get<Barrio[]>('/barrios'), []);
  const idBarrio = barrio ?? barrios.datos?.find((b) => b.nombre === 'Palermo')?.id ?? barrios.datos?.[0]?.id ?? null;
  const mesTexto = `${anio}-${String(mes).padStart(2, '0')}`;

  const ranking = useCarga(
    async () => (idBarrio ? api.get<ItemRanking[]>(`/consultas/ranking-barrio${qs({ barrio: idBarrio, mes: mesTexto, top: 10 })}`) : []),
    [idBarrio, mesTexto],
  );
  const maximo = Math.max(1, ...(ranking.datos ?? []).map((r) => r.checkins));

  const moverMes = (delta: number) => {
    const d = new Date(anio, mes - 1 + delta, 1);
    setAnio(d.getFullYear());
    setMes(d.getMonth() + 1);
  };

  return (
    <View style={s.pantalla}>
      <FlatList
        data={ranking.datos ?? []}
        keyExtractor={(r) => String(r.lugar.id)}
        contentContainerStyle={[s.contenido, { paddingTop: 4 }]}
        ListHeaderComponent={
          <View>
            <Selector
              etiqueta="Barrio"
              opciones={(barrios.datos ?? []).map((b) => ({ id: b.id, etiqueta: nombrePropio(b.nombre), detalle: `Comuna ${b.comuna}` }))}
              valor={idBarrio}
              onCambiar={setBarrio}
              permitirVacio={false}
            />
            <View style={[s.tarjeta, { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8 }]}>
              <BotonMes icono="chevron-back" onPress={() => moverMes(-1)} />
              <Text style={{ fontSize: 20, fontFamily: fuentes.titulo, color: colores.texto }}>{MESES[mes - 1]} {anio}</Text>
              <BotonMes icono="chevron-forward" onPress={() => moverMes(1)} />
            </View>
          </View>
        }
        renderItem={({ item }) => {
          const podio = item.puesto <= 3;
          return (
            <Pressable onPress={() => router.push(`/lugar/${item.lugar.id}`)}
              style={({ pressed }) => [s.tarjeta, { flexDirection: 'row', alignItems: 'center', gap: 12, opacity: pressed ? 0.85 : 1 }]}>
              <View style={{
                width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center',
                backgroundColor: podio ? MEDALLAS[item.puesto - 1] : colores.primarioClaro,
              }}>
                {podio
                  ? <Ionicons name="trophy" size={17} color={colores.blanco} />
                  : <Text style={{ fontFamily: fuentes.extra, color: colores.suave }}>{item.puesto}</Text>}
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontFamily: fuentes.titulo, fontSize: 17, color: colores.texto }} numberOfLines={1}>{nombrePropio(item.lugar.nombre)}</Text>
                <Text style={[s.suave, { fontSize: 12 }]} numberOfLines={1}>{nombrePropio(item.categoria)}</Text>
                <View style={{ height: 4, borderRadius: 2, backgroundColor: colores.primarioClaro, marginTop: 6 }}>
                  <View style={{ width: `${(100 * item.checkins) / maximo}%`, height: 4, borderRadius: 2, backgroundColor: podio ? colores.acento : colores.primario }} />
                </View>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={{ fontFamily: fuentes.titulo, fontSize: 22, color: colores.primario }}>{item.checkins}</Text>
                <Text style={{ fontFamily: fuentes.medio, fontSize: 10, color: colores.suave }}>check-ins</Text>
              </View>
            </Pressable>
          );
        }}
        ListFooterComponent={
          <Estado
            cargando={ranking.cargando}
            error={ranking.error ?? barrios.error}
            onReintentar={ranking.recargar}
            vacio={!ranking.cargando && (ranking.datos ?? []).length === 0 && 'Sin check-ins ese mes en este barrio'}
          />
        }
      />
    </View>
  );
}

function BotonMes({ icono, onPress }: { icono: 'chevron-back' | 'chevron-forward'; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} hitSlop={10} style={{
      width: 36, height: 36, borderRadius: 18, backgroundColor: colores.primarioClaro, alignItems: 'center', justifyContent: 'center',
    }}>
      <Ionicons name={icono} size={18} color={colores.primario} />
    </Pressable>
  );
}
