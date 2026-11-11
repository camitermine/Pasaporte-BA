// Versión web del mapa: react-native-maps no funciona en navegador, así que embebemos
// OpenStreetMap centrado en el punto elegido. La lista de abajo muestra los lugares.

import { View } from 'react-native';

import type { PropsMapa } from './Mapa';

export function Mapa({ punto, radio }: PropsMapa) {
  const dLat = Math.max(0.006, radio / 110_000);
  const dLon = Math.max(0.008, radio / 90_000);
  const bbox = [punto.lon - dLon, punto.lat - dLat, punto.lon + dLon, punto.lat + dLat].join(',');
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${punto.lat},${punto.lon}`;
  return (
    <View style={{ height: 300, borderRadius: 20, overflow: 'hidden', marginBottom: 16 }}>
      <iframe title="Mapa" src={src} style={{ border: 0, width: '100%', height: '100%' }} />
    </View>
  );
}
