import { router } from 'expo-router';
import { FlatList, View } from 'react-native';

import { ItemLugar } from '@/components/Items';
import { Estado, s } from '@/components/ui';
import { qs, usePaginado } from '@/lib/api';
import type { Lugar } from '@/lib/tipos';

export default function Favoritos() {
  const lista = usePaginado<Lugar>((cursor) => `/me/favoritos${qs({ cursor, limite: 30 })}`, []);
  return (
    <View style={s.pantalla}>
      <FlatList data={lista.items} keyExtractor={(l) => String(l.id)} contentContainerStyle={s.contenido}
        renderItem={({ item }) => <ItemLugar lugar={item} onPress={() => router.push(`/lugar/${item.id}`)} />}
        ListFooterComponent={<Estado cargando={lista.cargando} error={lista.error} onReintentar={lista.recargar}
          vacio={!lista.cargando && lista.items.length === 0 && 'Todavía no guardaste lugares'} />} />
    </View>
  );
}
