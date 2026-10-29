import { router } from 'expo-router';
import { FlatList, Text, View } from 'react-native';

import { avisar, Boton, confirmar, Estado, s, Tarjeta } from '@/components/ui';
import { mensajeError, useApi, useCarga } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { SugerenciaLugar } from '@/lib/tipos';

export default function ModerarSugerencias() {
  const api = useApi();
  const { usuario } = useConfig();
  const lista = useCarga(() => api.get<SugerenciaLugar[]>('/sugerencias?estado=pendiente'), []);

  const revisar = async (item: SugerenciaLugar, aprobar: boolean) => {
    const accion = aprobar ? 'aprobar y publicar' : 'rechazar';
    if (!(await confirmar('Revisar sugerencia', `¿Querés ${accion} “${item.nombre}”?`, aprobar ? 'Aprobar' : 'Rechazar'))) return;
    try {
      const resultado = await api.put<SugerenciaLugar>(`/sugerencias/${item.id}/revision`, {
        aprobar, motivo: aprobar ? 'Aprobada por moderación' : 'La propuesta no cumple los criterios del catálogo',
      });
      lista.recargar();
      if (resultado.id_lugar_creado) router.push(`/lugar/${resultado.id_lugar_creado}`);
    } catch (e) { avisar('No se pudo revisar', mensajeError(e)); }
  };

  if (usuario?.rol !== 'admin') return <View style={[s.pantalla, s.contenido]}><Text>Acceso exclusivo para administradores.</Text></View>;
  return <View style={s.pantalla}>
    <FlatList data={lista.datos ?? []} keyExtractor={(x) => String(x.id)} contentContainerStyle={s.contenido}
      renderItem={({ item }) => <Tarjeta>
        <Text style={s.titulo}>{item.nombre}</Text>
        <Text style={s.suave}>{item.categoria.nombre} · {item.barrio?.nombre ?? 'Sin barrio'}</Text>
        <Text style={s.suave}>{item.direccion ?? 'Sin dirección'} · @{item.usuario.nombre}</Text>
        {item.comentario ? <Text style={{ marginVertical: 8 }}>{item.comentario}</Text> : null}
        <View style={s.filaBotones}>
          <Boton titulo="Aprobar" estilo={{ flex: 1 }} onPress={() => revisar(item, true)} />
          <Boton titulo="Rechazar" variante="peligro" estilo={{ flex: 1 }} onPress={() => revisar(item, false)} />
        </View>
      </Tarjeta>}
      ListFooterComponent={<Estado cargando={lista.cargando} error={lista.error} onReintentar={lista.recargar}
        vacio={!lista.cargando && (lista.datos?.length ?? 0) === 0 && 'No hay sugerencias pendientes'} />} />
  </View>;
}
