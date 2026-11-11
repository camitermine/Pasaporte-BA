// Mi pasaporte: barrios visitados (consulta compleja) e historial de check-ins del usuario actual.

import Ionicons from '@expo/vector-icons/Ionicons';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { FlatList, Text, View } from 'react-native';

import { ItemCheckin } from '@/components/Items';
import { colores, Estado, fuentes, nombrePropio, s, Seccion, Sobretitulo } from '@/components/ui';
import { qs, useApi, useCarga, usePaginado } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Barrio, Checkin, Pasaporte } from '@/lib/tipos';

const COLORES_SELLO = [colores.primario, colores.acento, '#6E56CF', '#B5652B', '#1F7A8C'];

export default function PasaporteScreen() {
  const { usuario } = useConfig();
  return usuario ? <Contenido idUsuario={usuario.id} /> : null;
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
        contentContainerStyle={[s.contenido, { paddingTop: 4 }]}
        onEndReached={checkins.cargarMas}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={
          p ? (
            <View>
              <LinearGradient colors={['#1F5A40', '#143A2A']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                style={{ borderRadius: 24, padding: 20, overflow: 'hidden' }}>
                <View style={{ position: 'absolute', right: -24, bottom: -36, opacity: 0.08 }}>
                  <Ionicons name="earth" size={190} color={colores.blanco} />
                </View>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Sobretitulo color={colores.dorado} estilo={{ marginBottom: 0 }}>República de Buenos Aires · Pasaporte</Sobretitulo>
                  <Ionicons name="ribbon" size={18} color={colores.dorado} />
                </View>
                <Text style={{ color: colores.blanco, fontFamily: fuentes.titulo, fontSize: 30, marginTop: 14 }}>@{p.usuario.nombre}</Text>
                <View style={{ flexDirection: 'row', marginTop: 14, gap: 26 }}>
                  <Dato valor={p.total_checkins} texto="check-ins" />
                  <Dato valor={p.lugares_distintos} texto="lugares" />
                  <Dato valor={p.barrios_visitados.length} texto="barrios" />
                </View>
                <View style={{ height: 6, backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 3, marginTop: 18 }}>
                  <View style={{ width: `${p.progreso}%`, height: 6, backgroundColor: colores.dorado, borderRadius: 3 }} />
                </View>
                <Text style={{ color: 'rgba(255,255,255,0.85)', marginTop: 8, fontSize: 12, fontFamily: fuentes.medio }}>
                  {p.progreso}% de los barrios de la Ciudad
                </Text>
              </LinearGradient>

              <Seccion sobretitulo={`${p.barrios_visitados.length} conseguidos`} titulo="Sellos por barrio" />
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 14 }}>
                {p.barrios_visitados.map((b, i) => (
                  <Sello key={b.barrio.id} barrio={b.barrio} checkins={b.checkins} color={COLORES_SELLO[i % COLORES_SELLO.length]} />
                ))}
                {p.barrios_faltantes.map((b) => <Sello key={b.id} barrio={b} />)}
              </View>
              <Seccion sobretitulo="Historial" titulo="Mis check-ins" />
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

/** Sello circular de un barrio: con color si fue visitado, punteado si falta. */
function Sello({ barrio, checkins, color }: { barrio: Barrio; checkins?: number; color?: string }) {
  const visitado = !!color;
  return (
    <View style={{ width: '25%', alignItems: 'center' }}>
      <View style={{
        width: 62, height: 62, borderRadius: 31, alignItems: 'center', justifyContent: 'center',
        borderWidth: 2, borderStyle: visitado ? 'solid' : 'dashed',
        borderColor: visitado ? color : colores.borde,
        backgroundColor: visitado ? `${color}18` : 'transparent',
        transform: [{ rotate: visitado ? `${(barrio.id % 5) * 4 - 8}deg` : '0deg' }],
      }}>
        {visitado ? (
          <>
            <Text style={{ fontFamily: fuentes.titulo, fontSize: 20, color }}>{checkins}</Text>
            <Text style={{ fontFamily: fuentes.extra, fontSize: 7, letterSpacing: 1, color }}>VISITAS</Text>
          </>
        ) : (
          <Ionicons name="lock-closed-outline" size={18} color={colores.borde} />
        )}
      </View>
      <Text numberOfLines={2} style={{
        textAlign: 'center', fontSize: 11, marginTop: 5, lineHeight: 13,
        fontFamily: visitado ? fuentes.negrita : fuentes.medio, color: visitado ? colores.texto : colores.suave,
      }}>{nombrePropio(barrio.nombre)}</Text>
    </View>
  );
}

function Dato({ valor, texto }: { valor: number; texto: string }) {
  return (
    <View>
      <Text style={{ color: colores.blanco, fontSize: 26, fontFamily: fuentes.titulo }}>{valor}</Text>
      <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11, fontFamily: fuentes.medio }}>{texto}</Text>
    </View>
  );
}
