// Ranking mensual de lugares más visitados de un barrio (consulta compleja).

import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';

import { Selector } from '@/components/Selector';
import { colores, Estado, s } from '@/components/ui';
import { qs, useApi, useCarga } from '@/lib/api';
import type { Barrio, ItemRanking } from '@/lib/tipos';

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

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
        contentContainerStyle={s.contenido}
        ListHeaderComponent={
          <View>
            <Selector
              etiqueta="Barrio"
              opciones={(barrios.datos ?? []).map((b) => ({ id: b.id, etiqueta: b.nombre, detalle: `Comuna ${b.comuna}` }))}
              valor={idBarrio}
              onCambiar={setBarrio}
              permitirVacio={false}
            />
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <Pressable onPress={() => moverMes(-1)} hitSlop={12}><Text style={{ fontSize: 22, color: colores.primario }}>‹</Text></Pressable>
              <Text style={{ fontSize: 16, fontWeight: '700', color: colores.texto }}>{MESES[mes - 1]} {anio}</Text>
              <Pressable onPress={() => moverMes(1)} hitSlop={12}><Text style={{ fontSize: 22, color: colores.primario }}>›</Text></Pressable>
            </View>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => router.push(`/lugar/${item.lugar.id}`)} style={[s.tarjeta, { flexDirection: 'row', alignItems: 'center', gap: 12 }]}>
            <Text style={{ fontSize: 20, fontWeight: '800', width: 32, color: item.puesto <= 3 ? colores.estrella : colores.suave }}>
              {item.puesto}
            </Text>
            <View style={{ flex: 1 }}>
              <Text style={{ fontWeight: '700', color: colores.texto }} numberOfLines={1}>{item.lugar.nombre}</Text>
              <Text style={s.suave}>{item.categoria}</Text>
            </View>
            <Text style={{ fontWeight: '800', color: colores.primario }}>{item.checkins}</Text>
          </Pressable>
        )}
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
