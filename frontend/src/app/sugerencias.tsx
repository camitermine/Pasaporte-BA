import { router } from 'expo-router';
import { FlatList, Text, View } from 'react-native';

import { Boton, Chip, Estado, formatearFecha, s, Tarjeta } from '@/components/ui';
import { useApi, useCarga } from '@/lib/api';
import type { SugerenciaLugar } from '@/lib/tipos';

export default function MisSugerencias() {
  const api = useApi();
  const lista = useCarga(() => api.get<SugerenciaLugar[]>('/sugerencias'), []);
  return (
    <View style={s.pantalla}>
      <FlatList data={lista.datos ?? []} keyExtractor={(x) => String(x.id)} contentContainerStyle={s.contenido}
        ListHeaderComponent={<Boton titulo="Sugerir un lugar" onPress={() => router.push('/sugerencia/form')} />}
        renderItem={({ item }) => <Tarjeta>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
            <Text style={[s.titulo, { flex: 1 }]}>{item.nombre}</Text><Chip texto={item.estado} activo={item.estado === 'aprobada'} />
          </View>
          <Text style={s.suave}>{item.categoria.nombre} · {item.barrio?.nombre ?? 'Barrio sin definir'}</Text>
          <Text style={s.suave}>{formatearFecha(item.fecha_alta)}</Text>
          {item.motivo_revision ? <Text style={{ marginTop: 8 }}>Respuesta: {item.motivo_revision}</Text> : null}
        </Tarjeta>}
        ListFooterComponent={<Estado cargando={lista.cargando} error={lista.error} onReintentar={lista.recargar}
          vacio={!lista.cargando && (lista.datos?.length ?? 0) === 0 && 'No enviaste sugerencias'} />} />
    </View>
  );
}
