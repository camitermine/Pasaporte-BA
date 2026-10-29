// Cerca: lugares a menos de X metros de la ubicación actual (o de un punto de prueba).

import * as Location from 'expo-location';
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, Text, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';

import { ItemLugar } from '@/components/Items';
import { Boton, Chip, Estado, s } from '@/components/ui';
import { mensajeError, qs, useApi, useCarga } from '@/lib/api';
import type { LugarCercano } from '@/lib/tipos';

const RADIOS = [500, 1000, 2000, 5000];
const OBELISCO = { lat: -34.6037, lon: -58.3816 };

export default function Cerca() {
  const api = useApi();
  const [radio, setRadio] = useState(1000);
  const [punto, setPunto] = useState<{ lat: number; lon: number; nombre: string } | null>(null);
  const [ubicando, setUbicando] = useState(false);
  const [errorUbicacion, setErrorUbicacion] = useState<string | null>(null);

  const usarMiUbicacion = async () => {
    setUbicando(true);
    setErrorUbicacion(null);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') throw new Error('Sin permiso de ubicación');
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setPunto({ lat: pos.coords.latitude, lon: pos.coords.longitude, nombre: 'Mi ubicación' });
    } catch (e) {
      setErrorUbicacion(mensajeError(e));
    } finally {
      setUbicando(false);
    }
  };

  const resultado = useCarga(
    async () =>
      punto ? api.get<LugarCercano[]>(`/lugares/cercanos${qs({ lat: punto.lat, lon: punto.lon, radio_m: radio, limite: 30 })}`) : [],
    [punto?.lat, punto?.lon, radio],
  );

  return (
    <View style={s.pantalla}>
      <FlatList
        data={resultado.datos ?? []}
        keyExtractor={(r) => String(r.lugar.id)}
        contentContainerStyle={s.contenido}
        ListHeaderComponent={
          <View>
            <View style={s.filaBotones}>
              <Boton titulo="📍 Mi ubicación" onPress={usarMiUbicacion} cargando={ubicando} estilo={{ flex: 1 }} />
              <Boton titulo="Obelisco (prueba)" variante="secundario" estilo={{ flex: 1 }}
                onPress={() => setPunto({ ...OBELISCO, nombre: 'Obelisco' })} />
            </View>
            {errorUbicacion ? <Text style={{ color: 'red', marginTop: 8 }}>{errorUbicacion}</Text> : null}
            <Text style={s.subtitulo}>Radio</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
              {RADIOS.map((r) => (
                <Chip key={r} texto={r >= 1000 ? `${r / 1000} km` : `${r} m`} activo={radio === r} onPress={() => setRadio(r)} />
              ))}
            </View>
            {punto && (
              <>
                <Text style={[s.suave, { marginBottom: 8 }]}>
                  Desde {punto.nombre} ({punto.lat.toFixed(4)}, {punto.lon.toFixed(4)})
                </Text>
                <MapView
                  style={{ height: 300, borderRadius: 12, marginBottom: 16 }}
                  region={{
                    latitude: punto.lat, longitude: punto.lon,
                    latitudeDelta: Math.max(0.012, radio / 55_000),
                    longitudeDelta: Math.max(0.012, radio / 45_000),
                  }}
                  showsUserLocation={punto.nombre === 'Mi ubicación'}>
                  <Marker coordinate={{ latitude: punto.lat, longitude: punto.lon }} title={punto.nombre} pinColor="#2563EB" />
                  {(resultado.datos ?? []).filter((x) => x.lugar.latitud !== null && x.lugar.longitud !== null).map((x) => (
                    <Marker key={x.lugar.id}
                      coordinate={{ latitude: x.lugar.latitud!, longitude: x.lugar.longitud! }}
                      title={x.lugar.nombre}
                      description={`${x.lugar.categoria.nombre} · ${Math.round(x.distancia_m)} m`}
                      onCalloutPress={() => router.push(`/lugar/${x.lugar.id}`)} />
                  ))}
                </MapView>
              </>
            )}
          </View>
        }
        renderItem={({ item }) => (
          <ItemLugar lugar={item.lugar} extra={`${Math.round(item.distancia_m)} m`} onPress={() => router.push(`/lugar/${item.lugar.id}`)} />
        )}
        ListFooterComponent={
          <Estado
            cargando={!!punto && resultado.cargando}
            error={resultado.error}
            onReintentar={resultado.recargar}
            vacio={
              !punto ? 'Elegí un punto de partida para ver los lugares cercanos'
                : !resultado.cargando && (resultado.datos ?? []).length === 0 && 'No hay lugares en ese radio'
            }
          />
        }
      />
    </View>
  );
}
