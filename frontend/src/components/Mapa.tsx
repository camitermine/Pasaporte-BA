// Mapa de lugares cercanos (iOS/Android). En web se usa Mapa.web.tsx, porque react-native-maps no soporta web.

import { router } from 'expo-router';
import MapView, { Marker } from 'react-native-maps';

import type { LugarCercano } from '@/lib/tipos';
import { colores, tipoDe } from './ui';

export interface PropsMapa {
  punto: { lat: number; lon: number; nombre: string };
  radio: number;
  lugares: LugarCercano[];
}

export function Mapa({ punto, radio, lugares }: PropsMapa) {
  return (
    <MapView
      style={{ height: 300, borderRadius: 20, marginBottom: 16 }}
      region={{
        latitude: punto.lat, longitude: punto.lon,
        latitudeDelta: Math.max(0.012, radio / 55_000),
        longitudeDelta: Math.max(0.012, radio / 45_000),
      }}
      showsUserLocation={punto.nombre === 'Mi ubicación'}>
      <Marker coordinate={{ latitude: punto.lat, longitude: punto.lon }} title={punto.nombre} pinColor={colores.acento} />
      {lugares.filter((x) => x.lugar.latitud !== null && x.lugar.longitud !== null).map((x) => (
        <Marker key={x.lugar.id}
          coordinate={{ latitude: x.lugar.latitud!, longitude: x.lugar.longitud! }}
          title={x.lugar.nombre}
          pinColor={tipoDe(x.lugar.categoria.tipo).color}
          description={`${x.lugar.categoria.nombre} · ${Math.round(x.distancia_m)} m`}
          onCalloutPress={() => router.push(`/lugar/${x.lugar.id}`)} />
      ))}
    </MapView>
  );
}
