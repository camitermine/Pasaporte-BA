// Inicio / Explorar: resumen del pasaporte y listado de lugares con filtros por barrio, categoría y texto.

import Ionicons from '@expo/vector-icons/Ionicons';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { FlatList, Pressable, Text, TextInput, View } from 'react-native';

import { ItemLugar } from '@/components/Items';
import { Selector } from '@/components/Selector';
import { colores, Estado, fuentes, nombrePropio, s, Seccion, Sobretitulo, tipoDe } from '@/components/ui';
import { qs, useApi, useCarga, usePaginado } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Barrio, Categoria, Lugar, Pasaporte } from '@/lib/tipos';

export default function Explorar() {
  const api = useApi();
  const { usuario } = useConfig();
  const [texto, setTexto] = useState('');
  const [q, setQ] = useState('');
  const [barrio, setBarrio] = useState<number | null>(null);
  const [tipo, setTipo] = useState<string | null>(null);
  const [categoria, setCategoria] = useState<number | null>(null);

  // Espera a que el usuario deje de tipear antes de buscar
  useEffect(() => {
    const t = setTimeout(() => setQ(texto.trim()), 400);
    return () => clearTimeout(t);
  }, [texto]);

  const catalogo = useCarga(
    async () => ({
      barrios: await api.get<Barrio[]>('/barrios'),
      categorias: await api.get<Categoria[]>('/categorias'),
    }),
    [],
  );

  const pasaporte = useCarga(
    async () => (usuario ? api.get<Pasaporte>(`/consultas/pasaporte/${usuario.id}`) : null),
    [usuario?.id],
  );

  const lista = usePaginado<Lugar>(
    (cursor) => `/lugares${qs({ barrio, tipo, categoria, q, cursor, limite: 20 })}`,
    [barrio, tipo, categoria, q],
  );

  const tipos = Array.from(new Set((catalogo.datos?.categorias ?? []).map((c) => c.tipo)));
  const categoriasDelTipo = (catalogo.datos?.categorias ?? []).filter((c) => c.tipo === tipo);
  const hayFiltros = barrio !== null || tipo !== null || categoria !== null || q !== '';

  return (
    <View style={s.pantalla}>
      <FlatList
        data={lista.items}
        keyExtractor={(l) => String(l.id)}
        contentContainerStyle={[s.contenido, { paddingTop: 4 }]}
        onEndReached={lista.cargarMas}
        onEndReachedThreshold={0.4}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View>
            <Hero pasaporte={pasaporte.datos ?? null} nombre={usuario?.nombre ?? ''} />

            <Seccion sobretitulo="Seguí explorando" titulo="Lugares de la Ciudad"
              accion="Ver mapa" onAccion={() => router.push('/cerca')} />

            <View style={[s.input, { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12, borderRadius: 999 }]}>
              <Ionicons name="search" size={17} color={colores.suave} />
              <TextInput
                placeholder="Buscar por nombre…"
                placeholderTextColor={colores.suave}
                value={texto}
                onChangeText={setTexto}
                style={{ flex: 1, fontFamily: fuentes.medio, fontSize: 15, color: colores.texto, padding: 0 }}
              />
              {texto ? (
                <Pressable onPress={() => setTexto('')} hitSlop={8}>
                  <Ionicons name="close-circle" size={17} color={colores.suave} />
                </Pressable>
              ) : null}
            </View>

            <Text style={[s.etiqueta, { marginBottom: 8 }]}>Tipo de lugar</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
              <Pressable
                onPress={() => { setBarrio(null); setTipo(null); setCategoria(null); setTexto(''); }}
                style={[s.chip, !hayFiltros
                  ? { backgroundColor: colores.primario, borderColor: colores.primario }
                  : { backgroundColor: colores.blanco, borderColor: colores.borde }]}>
                <Ionicons name="sparkles" size={13} color={!hayFiltros ? colores.blanco : colores.primario} />
                <Text style={{ fontFamily: fuentes.medio, fontSize: 13, color: !hayFiltros ? colores.blanco : colores.texto }}>Todos</Text>
              </Pressable>
              {tipos.map((nombreTipo) => {
                const estilo = tipoDe(nombreTipo);
                const activo = tipo === nombreTipo;
                return (
                  <Pressable
                    key={nombreTipo}
                    onPress={() => {
                      setTipo(activo ? null : nombreTipo);
                      setCategoria(null);
                    }}
                    style={[s.chip, activo
                      ? { backgroundColor: estilo.color, borderColor: estilo.color }
                      : { backgroundColor: colores.blanco, borderColor: colores.borde }]}>
                    <Ionicons name={estilo.icono} size={13} color={activo ? colores.blanco : estilo.color} />
                    <Text style={{ fontFamily: fuentes.medio, fontSize: 13, color: activo ? colores.blanco : colores.texto }}>
                      {estilo.etiqueta}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={[s.etiqueta, { marginTop: 4, marginBottom: 8 }]}>Afinar búsqueda</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
              <Selector compacto
                etiqueta="Barrio"
                opciones={(catalogo.datos?.barrios ?? []).map((b) => ({ id: b.id, etiqueta: nombrePropio(b.nombre), detalle: `Comuna ${b.comuna}` }))}
                valor={barrio}
                onCambiar={setBarrio}
              />
              {tipo ? (
                <Selector compacto
                  etiqueta="Categoría"
                  opciones={categoriasDelTipo.map((c) => ({ id: c.id, etiqueta: nombrePropio(c.nombre) }))}
                  valor={categoria}
                  onCambiar={setCategoria}
                  textoVacio="Todas"
                />
              ) : null}
            </View>

            <Pressable
              onPress={() => router.push(usuario?.rol === 'admin' ? '/lugar/form' : '/sugerencia/form')}
              style={({ pressed }) => ({
                flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4, marginBottom: 14,
                borderWidth: 1.5, borderStyle: 'dashed', borderColor: colores.primario, borderRadius: 18,
                paddingVertical: 12, paddingHorizontal: 14, opacity: pressed ? 0.7 : 1,
              })}>
              <Ionicons name="add-circle" size={22} color={colores.primario} />
              <Text style={{ color: colores.primario, fontFamily: fuentes.negrita, flex: 1 }}>
                {usuario?.rol === 'admin' ? 'Agregar un lugar' : '¿Falta un lugar? Sugerilo'}
              </Text>
              <Ionicons name="chevron-forward" size={16} color={colores.primario} />
            </Pressable>
          </View>
        }
        renderItem={({ item }) => <ItemLugar lugar={item} onPress={() => router.push(`/lugar/${item.id}`)} />}
        ListFooterComponent={
          <Estado
            cargando={lista.cargando}
            error={lista.error}
            onReintentar={lista.recargar}
            vacio={!lista.cargando && lista.items.length === 0 && 'No hay lugares con esos filtros'}
          />
        }
      />
    </View>
  );
}

/** Tarjeta principal: progreso real del pasaporte del usuario (barrios visitados). */
function Hero({ pasaporte, nombre }: { pasaporte: Pasaporte | null; nombre: string }) {
  const visitados = pasaporte?.barrios_visitados.length ?? 0;
  const total = visitados + (pasaporte?.barrios_faltantes.length ?? 0);
  const progreso = pasaporte?.progreso ?? 0;
  const faltante = pasaporte?.barrios_faltantes[0]?.nombre;
  const siguiente = faltante ? nombrePropio(faltante) : undefined;
  const saludo = nombre.split(' ')[0];

  return (
    <View>
      <Pressable onPress={() => router.push('/pasaporte')}>
        <LinearGradient
          colors={['#3A8A66', colores.primario, '#143A2A']}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
          style={{ borderRadius: 26, padding: 22, paddingBottom: 46, overflow: 'hidden' }}>
          {/* Sellos decorativos */}
          <View style={{ position: 'absolute', right: -30, top: -30, width: 150, height: 150, borderRadius: 75, borderWidth: 18, borderColor: 'rgba(255,255,255,0.07)' }} />
          <View style={{ position: 'absolute', right: 40, top: 70, width: 70, height: 70, borderRadius: 35, borderWidth: 8, borderColor: 'rgba(242,196,109,0.18)' }} />

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Ionicons name="sparkles" size={12} color={colores.dorado} />
            <Sobretitulo color={colores.dorado} estilo={{ marginBottom: 0 }}>Tu desafío</Sobretitulo>
          </View>
          <Text style={{ color: colores.blanco, fontFamily: fuentes.titulo, fontSize: 30, lineHeight: 33, marginTop: 8 }}>
            {siguiente ? `Hola ${saludo}, ¿ya conocés ${siguiente}?` : `¡${saludo}, recorriste toda la Ciudad!`}
          </Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 18 }}>
            <View style={{ flex: 1, height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.25)' }}>
              <View style={{ width: `${progreso}%`, height: 6, borderRadius: 3, backgroundColor: colores.dorado }} />
            </View>
            <Text style={{ color: colores.blanco, fontFamily: fuentes.negrita, fontSize: 12 }}>{visitados} de {total || '–'}</Text>
            <View style={{ width: 34, height: 34, borderRadius: 17, borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.5)', alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="arrow-forward" size={16} color={colores.blanco} />
            </View>
          </View>
        </LinearGradient>
      </Pressable>

      <View style={[s.tarjeta, { flexDirection: 'row', marginHorizontal: 18, marginTop: -30, paddingVertical: 12 }]}>
        <Dato valor={pasaporte?.total_checkins} texto="Check-ins" />
        <View style={{ width: 1, backgroundColor: colores.borde }} />
        <Dato valor={visitados} texto="Barrios" />
        <View style={{ width: 1, backgroundColor: colores.borde }} />
        <Dato valor={pasaporte?.lugares_distintos} texto="Lugares" />
      </View>
    </View>
  );
}

function Dato({ valor, texto }: { valor: number | undefined; texto: string }) {
  return (
    <View style={{ flex: 1, alignItems: 'center' }}>
      <Text style={{ fontFamily: fuentes.titulo, fontSize: 26, color: colores.primario }}>{valor ?? '–'}</Text>
      <Text style={{ fontFamily: fuentes.medio, fontSize: 11, color: colores.suave }}>{texto}</Text>
    </View>
  );
}
