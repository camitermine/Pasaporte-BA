// Alta y modificación de un lugar. Con ?id= edita; sin id crea uno nuevo.

import * as Location from 'expo-location';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { Selector } from '@/components/Selector';
import { avisar, Boton, Campo, Estado, s } from '@/components/ui';
import { mensajeError, useApi, useCarga, volver } from '@/lib/api';
import type { Barrio, Categoria, Lugar, LugarIn } from '@/lib/tipos';

export default function FormLugar() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const api = useApi();
  const editando = !!id;

  const [nombre, setNombre] = useState('');
  const [direccion, setDireccion] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [idCategoria, setIdCategoria] = useState<number | null>(null);
  const [idBarrio, setIdBarrio] = useState<number | null>(null);
  const [guardando, setGuardando] = useState(false);

  const datos = useCarga(
    async () => ({
      barrios: await api.get<Barrio[]>('/barrios'),
      categorias: await api.get<Categoria[]>('/categorias'),
      lugar: editando ? await api.get<Lugar>(`/lugares/${id}`) : null,
    }),
    [id],
  );

  // Al editar, completar el formulario con los datos actuales (una sola vez).
  const lugar = datos.datos?.lugar;
  useEffect(() => {
    if (!lugar) return;
    setNombre(lugar.nombre);
    setDireccion(lugar.direccion ?? '');
    setLat(lugar.latitud !== null ? String(lugar.latitud) : '');
    setLon(lugar.longitud !== null ? String(lugar.longitud) : '');
    setIdCategoria(lugar.categoria.id);
    setIdBarrio(lugar.barrio.id);
  }, [lugar?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const usarUbicacion = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') throw new Error('Sin permiso de ubicación');
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setLat(pos.coords.latitude.toFixed(6));
      setLon(pos.coords.longitude.toFixed(6));
    } catch (e) {
      avisar('No se pudo obtener la ubicación', mensajeError(e));
    }
  };

  const guardar = async () => {
    const numero = (t: string) => (t.trim() === '' ? null : Number(t.replace(',', '.')));
    const cuerpo: LugarIn = {
      nombre: nombre.trim(),
      direccion: direccion.trim() || null,
      latitud: numero(lat),
      longitud: numero(lon),
      id_categoria: idCategoria!,
      id_barrio: idBarrio!,
    };
    if ((cuerpo.latitud === null) !== (cuerpo.longitud === null) || Number.isNaN(cuerpo.latitud) || Number.isNaN(cuerpo.longitud)) {
      avisar('Ubicación incompleta', 'Completá latitud y longitud (o dejá las dos vacías).');
      return;
    }
    setGuardando(true);
    try {
      const resultado = editando
        ? await api.put<Lugar>(`/lugares/${id}`, cuerpo)
        : await api.post<Lugar>('/lugares', cuerpo);
      if (editando) volver(`/lugar/${id}`);
      else router.replace(`/lugar/${resultado.id}`);
    } catch (e) {
      avisar('No se pudo guardar', mensajeError(e));
    } finally {
      setGuardando(false);
    }
  };

  if (!datos.datos) {
    return <View style={s.pantalla}><Estado cargando={datos.cargando} error={datos.error} onReintentar={datos.recargar} /></View>;
  }

  return (
    <ScrollView style={s.pantalla} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
      <Stack.Screen options={{ title: editando ? 'Editar lugar' : 'Nuevo lugar' }} />
      <Campo etiqueta="Nombre *" value={nombre} onChangeText={setNombre} placeholder="ej. Café Tortoni" />
      <Campo etiqueta="Dirección" value={direccion} onChangeText={setDireccion} placeholder="ej. Av. de Mayo 825" />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View style={{ flex: 1 }}><Campo etiqueta="Latitud" value={lat} onChangeText={setLat} keyboardType="numbers-and-punctuation" /></View>
        <View style={{ flex: 1 }}><Campo etiqueta="Longitud" value={lon} onChangeText={setLon} keyboardType="numbers-and-punctuation" /></View>
      </View>
      <Boton titulo="📍 Usar mi ubicación" variante="secundario" onPress={usarUbicacion} estilo={{ marginBottom: 12 }} />
      <Selector
        etiqueta="Categoría *"
        opciones={datos.datos.categorias.map((c) => ({ id: c.id, etiqueta: c.nombre, detalle: c.tipo }))}
        valor={idCategoria}
        onCambiar={setIdCategoria}
        textoVacio="Elegir…"
        permitirVacio={false}
      />
      <Selector
        etiqueta="Barrio *"
        opciones={datos.datos.barrios.map((b) => ({ id: b.id, etiqueta: b.nombre, detalle: `Comuna ${b.comuna}` }))}
        valor={idBarrio}
        onCambiar={setIdBarrio}
        textoVacio="Elegir…"
        permitirVacio={false}
      />
      <Boton
        titulo={editando ? 'Guardar cambios' : 'Crear lugar'}
        onPress={guardar}
        cargando={guardando}
        deshabilitado={!nombre.trim() || idCategoria === null || idBarrio === null}
      />
      <Text style={[s.suave, { marginTop: 12 }]}>* obligatorio</Text>
    </ScrollView>
  );
}
