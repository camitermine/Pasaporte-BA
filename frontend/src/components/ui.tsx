import { ReactNode } from 'react';
import {
  ActivityIndicator, Alert, Platform, Pressable, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle,
} from 'react-native';

export const colores = {
  primario: '#0E7490',
  primarioClaro: '#E0F2F7',
  texto: '#0F172A',
  suave: '#64748B',
  borde: '#E2E8F0',
  fondo: '#F8FAFC',
  blanco: '#FFFFFF',
  peligro: '#DC2626',
  mysql: '#00758F',
  hbase: '#C2410C',
  estrella: '#F59E0B',
};

export const colorMotor = (motor: string) => (motor === 'hbase' ? colores.hbase : colores.mysql);

export const mono = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' });

// ---------------------------------------------------------------- diálogos (funcionan también en web)

export function avisar(titulo: string, mensaje?: string) {
  if (Platform.OS === 'web') window.alert(mensaje ? `${titulo}\n\n${mensaje}` : titulo);
  else Alert.alert(titulo, mensaje);
}

export function confirmar(titulo: string, mensaje: string, accion = 'Aceptar'): Promise<boolean> {
  if (Platform.OS === 'web') return Promise.resolve(window.confirm(`${titulo}\n\n${mensaje}`));
  return new Promise((resolve) =>
    Alert.alert(titulo, mensaje, [
      { text: 'Cancelar', style: 'cancel', onPress: () => resolve(false) },
      { text: accion, style: 'destructive', onPress: () => resolve(true) },
    ]),
  );
}

// ---------------------------------------------------------------- componentes

export function Boton({
  titulo, onPress, variante = 'primario', deshabilitado, cargando, estilo,
}: {
  titulo: string;
  onPress: () => void;
  variante?: 'primario' | 'secundario' | 'peligro';
  deshabilitado?: boolean;
  cargando?: boolean;
  estilo?: ViewStyle;
}) {
  const fondo = { primario: colores.primario, secundario: colores.blanco, peligro: colores.peligro }[variante];
  const texto = variante === 'secundario' ? colores.primario : colores.blanco;
  return (
    <Pressable
      onPress={onPress}
      disabled={deshabilitado || cargando}
      style={({ pressed }) => [
        s.boton,
        { backgroundColor: fondo, opacity: deshabilitado ? 0.5 : pressed ? 0.8 : 1 },
        variante === 'secundario' && { borderWidth: 1, borderColor: colores.primario },
        estilo,
      ]}>
      {cargando ? <ActivityIndicator color={texto} /> : <Text style={[s.botonTexto, { color: texto }]}>{titulo}</Text>}
    </Pressable>
  );
}

export function Campo({ etiqueta, ...props }: TextInputProps & { etiqueta: string }) {
  return (
    <View style={{ marginBottom: 12 }}>
      <Text style={s.etiqueta}>{etiqueta}</Text>
      <TextInput placeholderTextColor={colores.suave} {...props} style={[s.input, props.multiline && { minHeight: 80 }]} />
    </View>
  );
}

export function Tarjeta({ children, estilo }: { children: ReactNode; estilo?: ViewStyle }) {
  return <View style={[s.tarjeta, estilo]}>{children}</View>;
}

export function Chip({ texto, activo, onPress, color }: { texto: string; activo?: boolean; onPress?: () => void; color?: string }) {
  const c = color ?? colores.primario;
  return (
    <Pressable onPress={onPress} style={[s.chip, { borderColor: c }, activo && { backgroundColor: c }]}>
      <Text style={{ color: activo ? colores.blanco : c, fontWeight: '600', fontSize: 13 }}>{texto}</Text>
    </Pressable>
  );
}

export function Estrellas({ valor, onCambiar, tamanio = 16 }: { valor: number | null; onCambiar?: (v: number | null) => void; tamanio?: number }) {
  return (
    <View style={{ flexDirection: 'row' }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Pressable key={n} disabled={!onCambiar} onPress={() => onCambiar?.(valor === n ? null : n)} hitSlop={6}>
          <Text style={{ fontSize: tamanio, color: valor && n <= valor ? colores.estrella : colores.borde, marginRight: 2 }}>★</Text>
        </Pressable>
      ))}
    </View>
  );
}

/** Estado de una carga: spinner, error con reintento o mensaje de vacío. */
export function Estado({ cargando, error, vacio, onReintentar }: {
  cargando?: boolean; error?: string | null; vacio?: string | false; onReintentar?: () => void;
}) {
  if (error) {
    return (
      <View style={s.estado}>
        <Text style={{ color: colores.peligro, textAlign: 'center', marginBottom: 12 }}>{error}</Text>
        {onReintentar && <Boton titulo="Reintentar" variante="secundario" onPress={onReintentar} />}
      </View>
    );
  }
  if (cargando) return <View style={s.estado}><ActivityIndicator color={colores.primario} /></View>;
  if (vacio) return <View style={s.estado}><Text style={{ color: colores.suave }}>{vacio}</Text></View>;
  return null;
}

export function Fila({ etiqueta, valor }: { etiqueta: string; valor: ReactNode }) {
  return (
    <View style={{ flexDirection: 'row', paddingVertical: 4 }}>
      <Text style={{ color: colores.suave, width: 96 }}>{etiqueta}</Text>
      <Text style={{ color: colores.texto, flex: 1 }}>{valor}</Text>
    </View>
  );
}

export function formatearFecha(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export const s = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: 16, paddingBottom: 32 },
  titulo: { fontSize: 20, fontWeight: '700', color: colores.texto, marginBottom: 4 },
  subtitulo: { fontSize: 15, fontWeight: '700', color: colores.texto, marginTop: 16, marginBottom: 8 },
  suave: { color: colores.suave, fontSize: 13 },
  boton: { paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  botonTexto: { fontWeight: '700', fontSize: 15 },
  etiqueta: { fontSize: 13, fontWeight: '600', color: colores.suave, marginBottom: 4 },
  input: {
    borderWidth: 1, borderColor: colores.borde, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10,
    fontSize: 15, backgroundColor: colores.blanco, color: colores.texto,
  },
  tarjeta: {
    backgroundColor: colores.blanco, borderRadius: 12, padding: 14, marginBottom: 10,
    borderWidth: 1, borderColor: colores.borde,
  },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, marginBottom: 8 },
  estado: { padding: 24, alignItems: 'center' },
  filaBotones: { flexDirection: 'row', gap: 8, marginTop: 8 },
});
