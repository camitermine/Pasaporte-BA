// Detalle de un lugar: datos, acciones (check-in, favorito, editar, borrar) y últimos check-ins.

import Ionicons from '@expo/vector-icons/Ionicons';
import { LinearGradient } from 'expo-linear-gradient';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ItemCheckin } from '@/components/Items';
import {
  avisar, Boton, colores, confirmar, Estado, Etiqueta, Fila, fuentes, nombrePropio, s, Seccion, Tarjeta, tipoDe,
} from '@/components/ui';
import { mensajeError, qs, useApi, useCarga, usePaginado, volver } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Checkin, Lugar } from '@/lib/tipos';

export default function DetalleLugar() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const api = useApi();
  const { usuario } = useConfig();
  const insets = useSafeAreaInsets();
  const [borrando, setBorrando] = useState(false);

  const lugar = useCarga(() => api.get<Lugar>(`/lugares/${id}`), [id]);
  const favorito = useCarga(() => api.get<{ favorito: boolean }>(`/me/favoritos/${id}`), [id]);
  const checkins = usePaginado<Checkin>((cursor) => `/lugares/${id}/checkins${qs({ cursor, limite: 10 })}`, [id]);
  const l = lugar.datos;

  const alternarFavorito = async () => {
    try {
      if (favorito.datos?.favorito) await api.del(`/me/favoritos/${id}`);
      else await api.put(`/me/favoritos/${id}`, {});
      favorito.recargar();
    } catch (e) {
      avisar('No se pudo actualizar', mensajeError(e));
    }
  };

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
      <View style={[s.pantalla, { paddingTop: insets.top + 56 }]}>
        <Estado cargando={lugar.cargando} error={lugar.error} onReintentar={lugar.recargar} />
      </View>
    );
  }

  const t = tipoDe(l.categoria.tipo);
  const esFavorito = !!favorito.datos?.favorito;

  return (
    <View style={s.pantalla}>
      <FlatList
        data={checkins.items}
        keyExtractor={(c) => String(c.id)}
        contentContainerStyle={{ paddingBottom: 40 }}
        ListHeaderComponent={
          <View>
            <LinearGradient
              colors={[t.fondo, colores.fondo]}
              style={{ paddingTop: insets.top + 64, paddingHorizontal: 18, paddingBottom: 8 }}>
              <View style={{ position: 'absolute', right: -40, top: insets.top + 10, opacity: 0.12 }}>
                <Ionicons name={t.icono} size={220} color={t.color} />
              </View>
              <Etiqueta texto={t.etiqueta.toUpperCase()} color={t.color} />
              <Text style={{ fontFamily: fuentes.titulo, fontSize: 34, lineHeight: 38, color: colores.texto, marginTop: 10 }}>
                {nombrePropio(l.nombre)}
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 }}>
                <Ionicons name="location" size={14} color={colores.acento} />
                <Text style={[s.suave, { fontSize: 14 }]}>
                  {l.barrio ? `${nombrePropio(l.barrio.nombre)} · Comuna ${l.barrio.comuna}` : 'Barrio sin definir'}
                </Text>
              </View>
            </LinearGradient>

            <View style={{ paddingHorizontal: 18 }}>
              <View style={[s.filaBotones, { marginTop: 14, marginBottom: 14 }]}>
                <Boton titulo="Hacer check-in" icono="checkmark-circle" estilo={{ flex: 1 }}
                  deshabilitado={!l.barrio}
                  onPress={() => router.push(`/checkin/form?idLugar=${l.id}`)} />
                <Pressable onPress={alternarFavorito} style={({ pressed }) => ({
                  width: 50, height: 50, borderRadius: 25, alignItems: 'center', justifyContent: 'center',
                  backgroundColor: esFavorito ? colores.acentoClaro : colores.blanco,
                  borderWidth: 1.5, borderColor: esFavorito ? colores.acentoClaro : colores.borde, opacity: pressed ? 0.7 : 1,
                })}>
                  <Ionicons name={esFavorito ? 'heart' : 'heart-outline'} size={22} color={colores.acento} />
                </Pressable>
              </View>
              {!l.barrio && (
                <Text style={[s.suave, { marginBottom: 12 }]}>Este lugar todavía no tiene barrio validado, por eso no admite check-in.</Text>
              )}

              <Tarjeta>
                <Fila icono="pricetag-outline" etiqueta="Categoría" valor={nombrePropio(l.categoria.nombre)} />
                <Fila icono="navigate-outline" etiqueta="Dirección" valor={l.direccion ?? '—'} />
                <Fila icono="locate-outline" etiqueta="Ubicación"
                  valor={l.latitud !== null ? `${l.latitud.toFixed(5)}, ${l.longitud?.toFixed(5)}` : '—'} />
                <Fila icono="document-text-outline" etiqueta="Fuente" valor={l.fuente ?? 'Cargado desde la app'} />
                <Fila icono="key-outline" etiqueta="ID" valor={String(l.id)} />
              </Tarjeta>

              {usuario?.rol === 'admin' && (
                <View style={s.filaBotones}>
                  <Boton titulo="Editar" icono="create-outline" variante="secundario" estilo={{ flex: 1 }}
                    onPress={() => router.push(`/lugar/form?id=${l.id}`)} />
                  <Boton titulo="Desactivar" icono="trash-outline" variante="peligro" estilo={{ flex: 1 }}
                    onPress={borrar} cargando={borrando} />
                </View>
              )}

              <Seccion sobretitulo="Actividad" titulo="Últimos check-ins" />
            </View>
          </View>
        }
        renderItem={({ item }) => (
          <View style={{ paddingHorizontal: 18 }}>
            <ItemCheckin
              checkin={item}
              mostrar="usuario"
              onPress={item.usuario.id === usuario?.id ? () => router.push(`/checkin/form?id=${item.id}`) : undefined}
            />
          </View>
        )}
        ListFooterComponent={
          <View style={{ paddingHorizontal: 18 }}>
            <Estado
              cargando={checkins.cargando}
              error={checkins.error}
              onReintentar={checkins.recargar}
              vacio={!checkins.cargando && checkins.items.length === 0 && 'Nadie hizo check-in acá todavía. ¡Sé el primero!'}
            />
            {checkins.hayMas && !checkins.cargando && (
              <Boton titulo="Ver más" variante="secundario" onPress={checkins.cargarMas} />
            )}
          </View>
        }
      />
    </View>
  );
}
