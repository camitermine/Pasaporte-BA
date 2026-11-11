// Selector con búsqueda en un modal (para barrios, categorías y usuarios).

import Ionicons from '@expo/vector-icons/Ionicons';
import { useMemo, useState } from 'react';
import { FlatList, Modal, Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colores, fuentes, s } from './ui';

export interface Opcion {
  id: number;
  etiqueta: string;
  detalle?: string;
}

const normalizar = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export function Selector({
  etiqueta, opciones, valor, onCambiar, textoVacio = 'Todos', permitirVacio = true, compacto = false,
}: {
  etiqueta: string;
  opciones: Opcion[];
  valor: number | null;
  onCambiar: (id: number | null) => void;
  textoVacio?: string;
  permitirVacio?: boolean;
  /** Muestra el selector como chip (para barras de filtros). */
  compacto?: boolean;
}) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const elegida = opciones.find((o) => o.id === valor);
  const filtradas = useMemo(
    () => opciones.filter((o) => normalizar(o.etiqueta).includes(normalizar(busqueda))),
    [opciones, busqueda],
  );

  const elegir = (id: number | null) => {
    onCambiar(id);
    setAbierto(false);
    setBusqueda('');
  };

  return (
    <View style={compacto ? undefined : { marginBottom: 12, flex: 1 }}>
      {compacto ? (
        <Pressable onPress={() => setAbierto(true)} style={[s.chip, elegida
          ? { backgroundColor: colores.primario, borderColor: colores.primario }
          : { backgroundColor: colores.blanco, borderColor: colores.borde }]}>
          <Text style={{ fontFamily: fuentes.medio, fontSize: 13, color: elegida ? colores.blanco : colores.texto }} numberOfLines={1}>
            {elegida ? elegida.etiqueta : etiqueta}
          </Text>
          <Ionicons name="chevron-down" size={13} color={elegida ? colores.blanco : colores.suave} />
        </Pressable>
      ) : (
        <>
          <Text style={s.etiqueta}>{etiqueta}</Text>
          <Pressable onPress={() => setAbierto(true)} style={[s.input, { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }]}>
            <Text style={{ color: elegida ? colores.texto : colores.suave, flex: 1, fontFamily: fuentes.medio, fontSize: 15 }} numberOfLines={1}>
              {elegida ? elegida.etiqueta : textoVacio}
            </Text>
            <Ionicons name="chevron-down" size={16} color={colores.suave} />
          </Pressable>
        </>
      )}

      <Modal visible={abierto} animationType="slide" onRequestClose={() => setAbierto(false)}>
        <SafeAreaView style={{ flex: 1, backgroundColor: colores.fondo }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 }}>
            <Text style={[s.titulo, { flex: 1, marginBottom: 0 }]}>{etiqueta}</Text>
            <Pressable onPress={() => setAbierto(false)} hitSlop={10}>
              <Text style={{ color: colores.primario, fontFamily: fuentes.negrita, fontSize: 16 }}>Cerrar</Text>
            </Pressable>
          </View>
          <View style={{ paddingHorizontal: 16 }}>
            <TextInput
              placeholder="Buscar…"
              placeholderTextColor={colores.suave}
              value={busqueda}
              onChangeText={setBusqueda}
              style={s.input}
              autoFocus
            />
          </View>
          <FlatList
            data={filtradas}
            keyExtractor={(o) => String(o.id)}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ padding: 16 }}
            ListHeaderComponent={
              permitirVacio ? (
                <Pressable onPress={() => elegir(null)} style={[s.tarjeta, valor === null && { borderWidth: 1.5, borderColor: colores.primario }]}>
                  <Text style={{ color: colores.suave, fontFamily: fuentes.medio }}>{textoVacio}</Text>
                </Pressable>
              ) : undefined
            }
            renderItem={({ item }) => (
              <Pressable onPress={() => elegir(item.id)} style={[s.tarjeta, item.id === valor && { borderWidth: 1.5, borderColor: colores.primario }]}>
                <Text style={{ color: colores.texto, fontFamily: fuentes.negrita }}>{item.etiqueta}</Text>
                {item.detalle ? <Text style={s.suave}>{item.detalle}</Text> : null}
              </Pressable>
            )}
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}
