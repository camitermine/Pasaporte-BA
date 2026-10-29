// Explorar: listado de lugares con filtros por barrio, categoría y texto.

import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { FlatList, Pressable, Text, TextInput, View } from 'react-native';

import { ItemLugar } from '@/components/Items';
import { Selector } from '@/components/Selector';
import { colores, Estado, s } from '@/components/ui';
import { qs, useApi, useCarga, usePaginado } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Barrio, Categoria, Lugar } from '@/lib/tipos';

export default function Explorar() {
  const api = useApi();
  const { usuario } = useConfig();
  const [texto, setTexto] = useState('');
  const [q, setQ] = useState('');
  const [barrio, setBarrio] = useState<number | null>(null);
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

  const lista = usePaginado<Lugar>(
    (cursor) => `/lugares${qs({ barrio, categoria, q, cursor, limite: 20 })}`,
    [barrio, categoria, q],
  );

  return (
    <View style={s.pantalla}>
      <FlatList
        data={lista.items}
        keyExtractor={(l) => String(l.id)}
        contentContainerStyle={s.contenido}
        onEndReached={lista.cargarMas}
        onEndReachedThreshold={0.4}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View>
            <TextInput
              placeholder="Buscar por nombre…"
              placeholderTextColor={colores.suave}
              value={texto}
              onChangeText={setTexto}
              style={[s.input, { marginBottom: 12 }]}
            />
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <Selector
                etiqueta="Barrio"
                opciones={(catalogo.datos?.barrios ?? []).map((b) => ({ id: b.id, etiqueta: b.nombre, detalle: `Comuna ${b.comuna}` }))}
                valor={barrio}
                onCambiar={setBarrio}
              />
              <Selector
                etiqueta="Categoría"
                opciones={(catalogo.datos?.categorias ?? []).map((c) => ({ id: c.id, etiqueta: c.nombre, detalle: c.tipo }))}
                valor={categoria}
                onCambiar={setCategoria}
                textoVacio="Todas"
              />
            </View>
            <Pressable
              onPress={() => router.push(usuario?.rol === 'admin' ? '/lugar/form' : '/sugerencia/form')}
              style={[s.tarjeta, { borderStyle: 'dashed', borderColor: colores.primario, alignItems: 'center' }]}>
              <Text style={{ color: colores.primario, fontWeight: '700' }}>
                {usuario?.rol === 'admin' ? '+ Agregar un lugar' : '+ Sugerir un lugar'}
              </Text>
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
