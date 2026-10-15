// Check-in: con ?idLugar= crea uno nuevo; con ?id= edita o borra uno existente.

import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { avisar, Boton, Campo, colores, confirmar, Estado, Estrellas, formatearFecha, s, Tarjeta } from '@/components/ui';
import { mensajeError, useApi, useCarga, volver } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Checkin, Lugar } from '@/lib/tipos';

export default function FormCheckin() {
  const { id, idLugar } = useLocalSearchParams<{ id?: string; idLugar?: string }>();
  const api = useApi();
  const { idUsuario } = useConfig();
  const editando = !!id;

  const [puntaje, setPuntaje] = useState<number | null>(null);
  const [comentario, setComentario] = useState('');
  const [guardando, setGuardando] = useState(false);

  const datos = useCarga(
    async () => {
      const checkin = editando ? await api.get<Checkin>(`/checkins/${id}`) : null;
      const lugar = await api.get<Lugar>(`/lugares/${checkin ? checkin.lugar.id : idLugar}`);
      return { checkin, lugar };
    },
    [id, idLugar],
  );

  const checkin = datos.datos?.checkin;
  useEffect(() => {
    if (!checkin) return;
    setPuntaje(checkin.puntaje);
    setComentario(checkin.comentario ?? '');
  }, [checkin?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const guardar = async () => {
    setGuardando(true);
    const cambios = { puntaje, comentario: comentario.trim() || null };
    try {
      if (editando) await api.put(`/checkins/${id}`, cambios);
      else await api.post('/checkins', { ...cambios, id_usuario: idUsuario, id_lugar: Number(idLugar) });
      volver(`/lugar/${datos.datos?.lugar.id ?? ''}`);
    } catch (e) {
      avisar('No se pudo guardar', mensajeError(e));
    } finally {
      setGuardando(false);
    }
  };

  const borrar = async () => {
    if (!(await confirmar('Borrar check-in', '¿Seguro que querés borrarlo?', 'Borrar'))) return;
    try {
      await api.del(`/checkins/${id}`);
      volver(`/lugar/${datos.datos?.lugar.id ?? ''}`);
    } catch (e) {
      avisar('No se pudo borrar', mensajeError(e));
    }
  };

  if (!datos.datos) {
    return <View style={s.pantalla}><Estado cargando={datos.cargando} error={datos.error} onReintentar={datos.recargar} /></View>;
  }
  const { lugar } = datos.datos;

  return (
    <ScrollView style={s.pantalla} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
      <Stack.Screen options={{ title: editando ? 'Editar check-in' : 'Nuevo check-in' }} />
      <Tarjeta>
        <Text style={s.titulo}>{lugar.nombre}</Text>
        <Text style={s.suave}>{lugar.categoria.nombre} · {lugar.barrio.nombre}</Text>
        {checkin && <Text style={[s.suave, { marginTop: 4 }]}>Check-in del {formatearFecha(checkin.fecha_hora)}</Text>}
      </Tarjeta>

      <Text style={s.etiqueta}>Puntaje (opcional, tocá de nuevo para quitarlo)</Text>
      <View style={{ marginBottom: 16 }}>
        <Estrellas valor={puntaje} onCambiar={setPuntaje} tamanio={36} />
      </View>
      <Campo
        etiqueta={`Comentario (${comentario.length}/280)`}
        value={comentario}
        onChangeText={(t) => setComentario(t.slice(0, 280))}
        multiline
        placeholder="¿Qué te pareció?"
      />
      <Boton titulo={editando ? 'Guardar cambios' : '✓ Hacer check-in'} onPress={guardar} cargando={guardando}
        deshabilitado={!editando && !idUsuario} />
      {editando && <Boton titulo="Borrar check-in" variante="peligro" onPress={borrar} estilo={{ marginTop: 8 }} />}
      {!editando && !idUsuario && (
        <Text style={{ color: colores.peligro, marginTop: 8 }}>Elegí un usuario en Ajustes primero.</Text>
      )}
    </ScrollView>
  );
}
