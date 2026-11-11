// Check-in: con ?idLugar= crea uno nuevo; con ?id= edita o borra uno existente.

import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';

import { avisar, Boton, Campo, confirmar, Estado, Estrellas, formatearFecha, IconoTipo, nombrePropio, s, Tarjeta } from '@/components/ui';
import { mensajeError, useApi, useCarga, volver } from '@/lib/api';
import type { Checkin, Lugar } from '@/lib/tipos';

export default function FormCheckin() {
  const { id, idLugar } = useLocalSearchParams<{ id?: string; idLugar?: string }>();
  const api = useApi();
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
    // El formulario local se inicializa cuando termina la carga del registro.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPuntaje(checkin.puntaje);
    setComentario(checkin.comentario ?? '');
  }, [checkin?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const guardar = async () => {
    setGuardando(true);
    const cambios = { puntaje, comentario: comentario.trim() || null };
    try {
      if (editando) await api.put(`/checkins/${id}`, cambios);
      else await api.post('/checkins', { ...cambios, id_lugar: Number(idLugar) });
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
      <Tarjeta estilo={{ flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <IconoTipo tipo={lugar.categoria.tipo} tamanio={58} />
        <View style={{ flex: 1 }}>
          <Text style={[s.titulo, { fontSize: 22 }]}>{nombrePropio(lugar.nombre)}</Text>
          <Text style={s.suave}>
            {nombrePropio(lugar.categoria.nombre)} · {lugar.barrio ? nombrePropio(lugar.barrio.nombre) : 'Barrio sin definir'}
          </Text>
          {checkin && <Text style={[s.suave, { marginTop: 4 }]}>Check-in del {formatearFecha(checkin.fecha_hora)}</Text>}
        </View>
      </Tarjeta>

      <Text style={s.etiqueta}>¿Cómo estuvo? (opcional, tocá de nuevo para quitarlo)</Text>
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
      <Boton titulo={editando ? 'Guardar cambios' : 'Hacer check-in'} icono="checkmark-circle" onPress={guardar} cargando={guardando} />
      {editando && <Boton titulo="Borrar check-in" icono="trash-outline" variante="peligro" onPress={borrar} estilo={{ marginTop: 8 }} />}
    </ScrollView>
  );
}
