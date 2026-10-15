// Mi pasaporte: barrios visitados (consulta compleja) e historial de check-ins del usuario actual.

import { router } from 'expo-router';
import { FlatList, Text, View } from 'react-native';

import { ItemCheckin } from '@/components/Items';
import { Boton, Chip, colores, Estado, s, Tarjeta } from '@/components/ui';
import { qs, useApi, useCarga, usePaginado } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Checkin, Pasaporte } from '@/lib/tipos';

export default function PasaporteScreen() {
  const { idUsuario } = useConfig();
  if (idUsuario === null) {
    return (
      <View style={[s.pantalla, s.contenido, { justifyContent: 'center' }]}>
        <Text style={[s.titulo, { textAlign: 'center' }]}>¿Quién sos?</Text>
        <Text style={[s.suave, { textAlign: 'center', marginBottom: 16 }]}>Elegí un usuario en Ajustes para ver tu pasaporte.</Text>
        <Boton titulo="Ir a Ajustes" onPress={() => router.push('/ajustes')} />
      </View>
    );
  }
  return <Contenido idUsuario={idUsuario} />;
}

function Contenido({ idUsuario }: { idUsuario: number }) {
  const api = useApi();
  const pasaporte = useCarga(() => api.get<Pasaporte>(`/consultas/pasaporte/${idUsuario}`), [idUsuario]);
  const checkins = usePaginado<Checkin>(
    (cursor) => `/usuarios/${idUsuario}/checkins${qs({ cursor, limite: 15 })}`,
    [idUsuario],
  );
  const p = pasaporte.datos;

  return (
    <View style={s.pantalla}>
      <FlatList
        data={checkins.items}
        keyExtractor={(c) => String(c.id)}
        contentContainerStyle={s.contenido}
        onEndReached={checkins.cargarMas}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={
          p ? (
            <View>
              <Tarjeta estilo={{ backgroundColor: colores.primario, borderColor: colores.primario }}>
                <Text style={{ color: colores.blanco, fontSize: 13, opacity: 0.8 }}>PASAPORTE BA</Text>
                <Text style={{ color: colores.blanco, fontSize: 22, fontWeight: '800' }}>@{p.usuario.nombre}</Text>
                <View style={{ flexDirection: 'row', marginTop: 12, gap: 20 }}>
                  <Dato valor={p.total_checkins} texto="check-ins" />
                  <Dato valor={p.lugares_distintos} texto="lugares" />
                  <Dato valor={p.barrios_visitados.length} texto="barrios" />
                </View>
                <View style={{ height: 8, backgroundColor: 'rgba(255,255,255,0.3)', borderRadius: 4, marginTop: 14 }}>
                  <View style={{ width: `${p.progreso}%`, height: 8, backgroundColor: colores.blanco, borderRadius: 4 }} />
                </View>
                <Text style={{ color: colores.blanco, marginTop: 6, fontSize: 13 }}>{p.progreso}% de los barrios de la Ciudad</Text>
              </Tarjeta>

              <Text style={s.subtitulo}>Sellos por barrio</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                {p.barrios_visitados.map((b) => (
                  <Chip key={b.barrio.id} texto={`${b.barrio.nombre} · ${b.checkins}`} activo />
                ))}
              </View>
              {p.barrios_faltantes.length > 0 && (
                <>
                  <Text style={s.subtitulo}>Te faltan ({p.barrios_faltantes.length})</Text>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                    {p.barrios_faltantes.map((b) => (
                      <Chip key={b.id} texto={b.nombre} color={colores.suave} />
                    ))}
                  </View>
                </>
              )}
              <Text style={s.subtitulo}>Mis check-ins</Text>
            </View>
          ) : (
            <Estado cargando={pasaporte.cargando} error={pasaporte.error} onReintentar={pasaporte.recargar} />
          )
        }
        renderItem={({ item }) => (
          <ItemCheckin checkin={item} mostrar="lugar" onPress={() => router.push(`/checkin/form?id=${item.id}`)} />
        )}
        ListFooterComponent={
          <Estado
            cargando={checkins.cargando}
            error={checkins.error}
            onReintentar={checkins.recargar}
            vacio={!checkins.cargando && checkins.items.length === 0 && 'Todavía no hiciste check-ins'}
          />
        }
      />
    </View>
  );
}

function Dato({ valor, texto }: { valor: number; texto: string }) {
  return (
    <View>
      <Text style={{ color: colores.blanco, fontSize: 22, fontWeight: '800' }}>{valor}</Text>
      <Text style={{ color: colores.blanco, fontSize: 12, opacity: 0.85 }}>{texto}</Text>
    </View>
  );
}
