// Detalle de un lugar: datos, acciones (check-in, editar, borrar) y últimos check-ins.

import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { FlatList, Text, View } from 'react-native';

import { ItemCheckin } from '@/components/Items';
import { avisar, Boton, colores, confirmar, Estado, Fila, s, Tarjeta } from '@/components/ui';
import { mensajeError, qs, useApi, useCarga, usePaginado, volver } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Checkin, Lugar } from '@/lib/tipos';

export default function DetalleLugar() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const api = useApi();
  const { idUsuario } = useConfig();
  const [borrando, setBorrando] = useState(false);

  const lugar = useCarga(() => api.get<Lugar>(`/lugares/${id}`), [id]);
  const checkins = usePaginado<Checkin>((cursor) => `/lugares/${id}/checkins${qs({ cursor, limite: 10 })}`, [id]);
  const l = lugar.datos;

  const borrar = async () => {
    if (!(await confirmar('Borrar lugar', `¿Seguro que querés borrar "${l?.nombre}"?`, 'Borrar'))) return;
    setBorrando(true);
    try {
      await api.del(`/lugares/${id}`);
      volver('/');
    } catch (e) {
      avisar('No se pudo borrar', mensajeError(e));
    } finally {
      setBorrando(false);
    }
  };

  if (!l) {
    return (
      <View style={s.pantalla}>
        <Estado cargando={lugar.cargando} error={lugar.error} onReintentar={lugar.recargar} />
      </View>
    );
  }

  return (
    <View style={s.pantalla}>
      <Stack.Screen options={{ title: l.nombre }} />
      <FlatList
        data={checkins.items}
        keyExtractor={(c) => String(c.id)}
        contentContainerStyle={s.contenido}
        ListHeaderComponent={
          <View>
            <Tarjeta>
              <Text style={s.titulo}>{l.nombre}</Text>
              <Text style={[s.suave, { marginBottom: 8 }]}>{l.categoria.nombre} · {l.categoria.tipo}</Text>
              <Fila etiqueta="Barrio" valor={`${l.barrio.nombre} (Comuna ${l.barrio.comuna})`} />
              <Fila etiqueta="Dirección" valor={l.direccion ?? '—'} />
              <Fila etiqueta="Ubicación" valor={l.latitud !== null ? `${l.latitud}, ${l.longitud}` : '—'} />
              <Fila etiqueta="Fuente" valor={l.fuente ?? 'Cargado desde la app'} />
              <Fila etiqueta="ID" valor={String(l.id)} />
            </Tarjeta>

            <Boton
              titulo={idUsuario ? '✓ Hacer check-in' : 'Elegí un usuario en Ajustes para hacer check-in'}
              onPress={() => router.push(`/checkin/form?idLugar=${l.id}`)}
              deshabilitado={!idUsuario}
            />
            <View style={s.filaBotones}>
              <Boton titulo="Editar" variante="secundario" estilo={{ flex: 1 }} onPress={() => router.push(`/lugar/form?id=${l.id}`)} />
              <Boton titulo="Borrar" variante="peligro" estilo={{ flex: 1 }} onPress={borrar} cargando={borrando} />
            </View>

            <Text style={s.subtitulo}>Últimos check-ins</Text>
          </View>
        }
        renderItem={({ item }) => (
          <ItemCheckin
            checkin={item}
            mostrar="usuario"
            onPress={item.usuario.id === idUsuario ? () => router.push(`/checkin/form?id=${item.id}`) : undefined}
          />
        )}
        ListFooterComponent={
          <View>
            <Estado
              cargando={checkins.cargando}
              error={checkins.error}
              onReintentar={checkins.recargar}
              vacio={!checkins.cargando && checkins.items.length === 0 && 'Nadie hizo check-in acá todavía'}
            />
            {checkins.hayMas && !checkins.cargando && (
              <Boton titulo="Ver más" variante="secundario" onPress={checkins.cargarMas} />
            )}
            <Text style={[s.suave, { marginTop: 12, color: colores.suave }]}>
              Los check-ins de otros usuarios no se pueden editar.
            </Text>
          </View>
        }
      />
    </View>
  );
}
