import * as Location from 'expo-location';
import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { Selector } from '@/components/Selector';
import { avisar, Boton, Campo, Estado, s } from '@/components/ui';
import { mensajeError, useApi, useCarga, volver } from '@/lib/api';
import type { Barrio, Categoria } from '@/lib/tipos';

export default function FormSugerencia() {
  const api = useApi();
  const [nombre, setNombre] = useState('');
  const [direccion, setDireccion] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [comentario, setComentario] = useState('');
  const [idCategoria, setIdCategoria] = useState<number | null>(null);
  const [idBarrio, setIdBarrio] = useState<number | null>(null);
  const [guardando, setGuardando] = useState(false);
  const datos = useCarga(async () => ({
    barrios: await api.get<Barrio[]>('/barrios'), categorias: await api.get<Categoria[]>('/categorias'),
  }), []);

  const usarUbicacion = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') throw new Error('Sin permiso de ubicación');
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setLat(pos.coords.latitude.toFixed(7)); setLon(pos.coords.longitude.toFixed(7));
    } catch (e) { avisar('No se pudo obtener la ubicación', mensajeError(e)); }
  };

  const enviar = async () => {
    const numero = (t: string) => t.trim() ? Number(t.replace(',', '.')) : null;
    const latitud = numero(lat), longitud = numero(lon);
    if ((latitud === null) !== (longitud === null) || Number.isNaN(latitud) || Number.isNaN(longitud)) {
      avisar('Ubicación incompleta', 'Completá las dos coordenadas o dejalas vacías.'); return;
    }
    setGuardando(true);
    try {
      await api.post('/sugerencias', {
        nombre: nombre.trim(), direccion: direccion.trim() || null, latitud, longitud,
        id_categoria: idCategoria, id_barrio: idBarrio, comentario: comentario.trim() || null,
      });
      avisar('Sugerencia enviada', 'Un administrador la revisará antes de publicarla.');
      volver('/sugerencias');
    } catch (e) { avisar('No se pudo enviar', mensajeError(e)); }
    finally { setGuardando(false); }
  };

  if (!datos.datos) return <View style={s.pantalla}><Estado cargando={datos.cargando} error={datos.error} onReintentar={datos.recargar} /></View>;
  return <ScrollView style={s.pantalla} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
    <Text style={s.suave}>El lugar no se publica automáticamente. Primero pasa por moderación.</Text>
    <Campo etiqueta="Nombre *" value={nombre} onChangeText={setNombre} />
    <Campo etiqueta="Dirección" value={direccion} onChangeText={setDireccion} />
    <View style={{ flexDirection: 'row', gap: 8 }}>
      <View style={{ flex: 1 }}><Campo etiqueta="Latitud" value={lat} onChangeText={setLat} keyboardType="numbers-and-punctuation" /></View>
      <View style={{ flex: 1 }}><Campo etiqueta="Longitud" value={lon} onChangeText={setLon} keyboardType="numbers-and-punctuation" /></View>
    </View>
    <Boton titulo="Usar mi ubicación" variante="secundario" onPress={usarUbicacion} estilo={{ marginBottom: 12 }} />
    <Selector etiqueta="Categoría *" opciones={datos.datos.categorias.map((c) => ({ id: c.id, etiqueta: c.nombre, detalle: c.tipo }))}
      valor={idCategoria} onCambiar={setIdCategoria} permitirVacio={false} />
    <Selector etiqueta="Barrio" opciones={datos.datos.barrios.map((b) => ({ id: b.id, etiqueta: b.nombre, detalle: `Comuna ${b.comuna}` }))}
      valor={idBarrio} onCambiar={setIdBarrio} />
    <Campo etiqueta="Comentario para el administrador" value={comentario}
      onChangeText={(t) => setComentario(t.slice(0, 500))} multiline />
    <Boton titulo="Enviar sugerencia" onPress={enviar} cargando={guardando}
      deshabilitado={!nombre.trim() || idCategoria === null} />
  </ScrollView>;
}
