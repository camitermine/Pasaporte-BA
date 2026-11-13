// Selector con búsqueda en un modal (para barrios, categorías y usuarios).

import Ionicons from '@expo/vector-icons/Ionicons';
import { useMemo, useState } from 'react';
import { Modal, Platform, Pressable, ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
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
  const { width, height } = useWindowDimensions();
  const esEscritorioWeb = Platform.OS === 'web' && width >= 768;
  const altoModalEscritorio = Math.min(720, Math.max(420, height - 48));
  const altoListaEscritorio = altoModalEscritorio - 154;
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

      <Modal
        visible={abierto}
        transparent={esEscritorioWeb}
        animationType={esEscritorioWeb ? 'fade' : 'slide'}
        onRequestClose={() => setAbierto(false)}>
        <SafeAreaView style={esEscritorioWeb
          ? { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(23,33,29,0.45)' }
          : { flex: 1, backgroundColor: colores.fondo }}>
          <View style={esEscritorioWeb
            ? {
                width: '100%', maxWidth: 440, height: altoModalEscritorio,
                borderRadius: 24, overflow: 'hidden', backgroundColor: colores.fondo,
                boxShadow: '0 24px 70px rgba(23,33,29,0.24)',
              }
            : { flex: 1, backgroundColor: colores.fondo }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', padding: 18, paddingBottom: 14, gap: 12 }}>
              <View style={{ flex: 1 }}>
                <Text style={[s.titulo, { marginBottom: 0 }]}>{etiqueta}</Text>
                <Text style={s.suave}>{filtradas.length} opciones</Text>
              </View>
              <Pressable
                onPress={() => setAbierto(false)}
                hitSlop={10}
                accessibilityLabel="Cerrar selector"
                style={{ width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', backgroundColor: colores.primarioClaro }}>
                <Ionicons name="close" size={21} color={colores.primario} />
              </Pressable>
            </View>
            <View style={{ paddingHorizontal: 18 }}>
              <View style={[s.input, { flexDirection: 'row', alignItems: 'center', gap: 8 }]}>
                <Ionicons name="search" size={17} color={colores.suave} />
                <TextInput
                  placeholder="Buscar…"
                  placeholderTextColor={colores.suave}
                  value={busqueda}
                  onChangeText={setBusqueda}
                  style={{ flex: 1, padding: 0, color: colores.texto, fontFamily: fuentes.medio, fontSize: 15 }}
                  autoFocus
                />
              </View>
            </View>
            <ScrollView
              style={esEscritorioWeb
                ? { height: altoListaEscritorio, flexGrow: 0 }
                : { flex: 1, minHeight: 0 }}
              keyboardShouldPersistTaps="handled"
              keyboardDismissMode="on-drag"
              showsVerticalScrollIndicator
              contentContainerStyle={{ padding: 18, paddingTop: 14, paddingBottom: 32 }}>
              {permitirVacio ? (
                <OpcionSelector
                  etiqueta={textoVacio}
                  detalle="Quitar este filtro"
                  seleccionada={valor === null}
                  onPress={() => elegir(null)}
                />
              ) : null}
              {filtradas.length === 0 ? (
                <View style={s.estado}>
                  <Ionicons name="search-outline" size={28} color={colores.suave} />
                  <Text style={[s.suave, { marginTop: 8 }]}>No hay opciones con ese nombre</Text>
                </View>
              ) : filtradas.map((item) => (
                <OpcionSelector
                  key={item.id}
                  etiqueta={item.etiqueta}
                  detalle={item.detalle}
                  seleccionada={item.id === valor}
                  onPress={() => elegir(item.id)}
                />
              ))}
            </ScrollView>
          </View>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function OpcionSelector({ etiqueta, detalle, seleccionada, onPress }: {
  etiqueta: string;
  detalle?: string;
  seleccionada: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [{
        minHeight: 58, paddingHorizontal: 14, paddingVertical: 10, marginBottom: 8,
        borderRadius: 14, borderWidth: 1.5,
        borderColor: seleccionada ? colores.primario : colores.borde,
        backgroundColor: seleccionada ? colores.primarioClaro : colores.blanco,
        flexDirection: 'row', alignItems: 'center', gap: 12,
        opacity: pressed ? 0.72 : 1,
      }]}>
      <View style={{ flex: 1 }}>
        <Text style={{ color: colores.texto, fontFamily: fuentes.negrita, fontSize: 14 }}>{etiqueta}</Text>
        {detalle ? <Text style={[s.suave, { marginTop: 2 }]}>{detalle}</Text> : null}
      </View>
      {seleccionada ? <Ionicons name="checkmark-circle" size={21} color={colores.primario} /> : null}
    </Pressable>
  );
}
