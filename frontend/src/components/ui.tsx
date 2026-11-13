// Sistema visual de Pasaporte BA: paleta, tipografías y componentes base.
// Inspirado en el mockup de Figma (verde porteño, coral, fondo crema, DM Serif + Manrope).

import Ionicons from '@expo/vector-icons/Ionicons';
import { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator, Alert, Platform, Pressable, StyleSheet, Text, TextInput, TextInputProps, TextStyle, View, ViewStyle,
} from 'react-native';

export const colores = {
  primario: '#286B4E',
  primarioOscuro: '#1C4D38',
  primarioClaro: '#EDF1EB',
  acento: '#E35D4A',
  acentoClaro: '#FCE8E4',
  dorado: '#F2C46D',
  texto: '#17211D',
  suave: '#708079',
  borde: '#E4E8E1',
  fondo: '#FBFAF5',
  blanco: '#FFFFFF',
  peligro: '#C2412D',
  mysql: '#00758F',
  hbase: '#C2410C',
  estrella: '#F2A93B',
};

export const fuentes = {
  titulo: 'DMSerifDisplay_400Regular',
  tituloItalica: 'DMSerifDisplay_400Regular_Italic',
  regular: 'Manrope_400Regular',
  medio: 'Manrope_600SemiBold',
  negrita: 'Manrope_700Bold',
  extra: 'Manrope_800ExtraBold',
};

type Icono = ComponentProps<typeof Ionicons>['name'];

/** Color e ícono de cada tipo de categoría del dataset (reemplazan a las fotos del mockup). */
export const estiloTipo: Record<string, { color: string; fondo: string; icono: Icono; etiqueta: string }> = {
  cultura: { color: '#6E56CF', fondo: '#EFEBFB', icono: 'color-palette', etiqueta: 'Cultura' },
  patrimonio: { color: '#B5652B', fondo: '#F8EDE3', icono: 'business', etiqueta: 'Patrimonio' },
  'arte urbano': { color: '#E35D4A', fondo: '#FCE8E4', icono: 'brush', etiqueta: 'Arte urbano' },
  gastronomia: { color: '#286B4E', fondo: '#E3EFE8', icono: 'cafe', etiqueta: 'Gastronomía' },
};
const claveTipo = (tipo: string) => tipo.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export const tipoDe = (tipo: string) =>
  estiloTipo[claveTipo(tipo)] ?? { color: colores.suave, fondo: colores.primarioClaro, icono: 'location' as Icono, etiqueta: tipo };

export const colorMotor = (motor: string) => (motor === 'hbase' ? colores.hbase : colores.mysql);

export const mono = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' });

const sombra: ViewStyle = Platform.select({
  web: { boxShadow: '0 10px 24px rgba(35,60,48,0.08)' } as ViewStyle,
  default: { shadowColor: '#23403A', shadowOpacity: 0.08, shadowRadius: 14, shadowOffset: { width: 0, height: 8 }, elevation: 3 },
})!;

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
  titulo, onPress, variante = 'primario', deshabilitado, cargando, estilo, icono,
}: {
  titulo: string;
  onPress: () => void;
  variante?: 'primario' | 'secundario' | 'peligro' | 'suave';
  deshabilitado?: boolean;
  cargando?: boolean;
  estilo?: ViewStyle;
  icono?: Icono;
}) {
  const fondo = {
    primario: colores.primario, secundario: colores.blanco, peligro: colores.peligro, suave: colores.primarioClaro,
  }[variante];
  const texto = variante === 'secundario' || variante === 'suave' ? colores.primario : colores.blanco;
  return (
    <Pressable
      onPress={onPress}
      disabled={deshabilitado || cargando}
      style={({ pressed }) => [
        s.boton,
        { backgroundColor: fondo, opacity: deshabilitado ? 0.45 : pressed ? 0.85 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] },
        variante === 'secundario' && { borderWidth: 1.5, borderColor: colores.borde },
        estilo,
      ]}>
      {cargando ? <ActivityIndicator color={texto} /> : (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          {icono && <Ionicons name={icono} size={17} color={texto} />}
          <Text style={[s.botonTexto, { color: texto }]}>{titulo}</Text>
        </View>
      )}
    </Pressable>
  );
}

export function Campo({ etiqueta, ...props }: TextInputProps & { etiqueta: string }) {
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={s.etiqueta}>{etiqueta}</Text>
      <TextInput placeholderTextColor={colores.suave} {...props} style={[s.input, props.multiline && { minHeight: 90, textAlignVertical: 'top' }]} />
    </View>
  );
}

export function Tarjeta({ children, estilo }: { children: ReactNode; estilo?: ViewStyle }) {
  return <View style={[s.tarjeta, estilo]}>{children}</View>;
}

export function Chip({ texto, activo, onPress, color, icono }: {
  texto: string; activo?: boolean; onPress?: () => void; color?: string; icono?: Icono;
}) {
  const c = color ?? colores.primario;
  return (
    <Pressable onPress={onPress} disabled={!onPress}
      style={[s.chip, activo ? { backgroundColor: c, borderColor: c } : { borderColor: colores.borde, backgroundColor: colores.blanco }]}>
      {icono && <Ionicons name={icono} size={13} color={activo ? colores.blanco : c} />}
      <Text style={{ color: activo ? colores.blanco : colores.texto, fontFamily: fuentes.medio, fontSize: 13 }}>{texto}</Text>
    </Pressable>
  );
}

/** Etiqueta chica en mayúsculas espaciadas ("CERCA TUYO"). */
export function Sobretitulo({ children, color, estilo }: { children: ReactNode; color?: string; estilo?: TextStyle }) {
  return <Text style={[s.sobretitulo, color ? { color } : null, estilo]}>{children}</Text>;
}

/** Encabezado de sección: sobretítulo + título serif + acción opcional a la derecha. */
export function Seccion({ sobretitulo, titulo, accion, onAccion }: {
  sobretitulo?: string; titulo: string; accion?: string; onAccion?: () => void;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginTop: 22, marginBottom: 12 }}>
      <View style={{ flex: 1 }}>
        {sobretitulo && <Sobretitulo>{sobretitulo}</Sobretitulo>}
        <Text style={s.tituloSeccion}>{titulo}</Text>
      </View>
      {accion && (
        <Pressable onPress={onAccion} hitSlop={8} style={{ flexDirection: 'row', alignItems: 'center', gap: 4, paddingBottom: 4 }}>
          <Text style={{ color: colores.primario, fontFamily: fuentes.negrita, fontSize: 13 }}>{accion}</Text>
          <Ionicons name="arrow-forward" size={14} color={colores.primario} />
        </Pressable>
      )}
    </View>
  );
}

/** Ícono cuadrado con el color del tipo de lugar (lo usamos en lugar de fotos). */
export function IconoTipo({ tipo, tamanio = 64 }: { tipo: string; tamanio?: number }) {
  const t = tipoDe(tipo);
  return (
    <View style={{
      width: tamanio, height: tamanio, borderRadius: tamanio * 0.28, backgroundColor: t.fondo,
      alignItems: 'center', justifyContent: 'center',
    }}>
      <Ionicons name={t.icono} size={tamanio * 0.45} color={t.color} />
    </View>
  );
}

export function Etiqueta({ texto, color, fondo }: { texto: string; color: string; fondo?: string }) {
  return (
    <View style={{ alignSelf: 'flex-start', backgroundColor: fondo ?? color, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 3 }}>
      <Text style={{ color: fondo ? color : colores.blanco, fontFamily: fuentes.extra, fontSize: 10, letterSpacing: 0.3 }}>{texto}</Text>
    </View>
  );
}

export function Estrellas({ valor, onCambiar, tamanio = 16 }: { valor: number | null; onCambiar?: (v: number | null) => void; tamanio?: number }) {
  return (
    <View style={{ flexDirection: 'row', gap: 2 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Pressable key={n} disabled={!onCambiar} onPress={() => onCambiar?.(valor === n ? null : n)} hitSlop={6}>
          <Ionicons name={valor && n <= valor ? 'star' : 'star-outline'} size={tamanio}
            color={valor && n <= valor ? colores.estrella : colores.borde} />
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
        <Ionicons name="cloud-offline-outline" size={32} color={colores.peligro} />
        <Text style={{ color: colores.peligro, textAlign: 'center', marginVertical: 12, fontFamily: fuentes.medio }}>{error}</Text>
        {onReintentar && <Boton titulo="Reintentar" variante="secundario" onPress={onReintentar} />}
      </View>
    );
  }
  if (cargando) return <View style={s.estado}><ActivityIndicator color={colores.primario} /></View>;
  if (vacio) {
    return (
      <View style={s.estado}>
        <Ionicons name="map-outline" size={30} color={colores.suave} />
        <Text style={{ color: colores.suave, marginTop: 8, fontFamily: fuentes.medio, textAlign: 'center' }}>{vacio}</Text>
      </View>
    );
  }
  return null;
}

export function Fila({ etiqueta, valor, icono }: { etiqueta: string; valor: ReactNode; icono?: Icono }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 7, gap: 10 }}>
      {icono && <Ionicons name={icono} size={16} color={colores.suave} style={{ marginTop: 1 }} />}
      <Text style={{ color: colores.suave, width: 84, fontFamily: fuentes.medio, fontSize: 13 }}>{etiqueta}</Text>
      <Text style={{ color: colores.texto, flex: 1, fontFamily: fuentes.medio, fontSize: 14 }}>{valor}</Text>
    </View>
  );
}

const MINUSCULAS = new Set(['de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'en', 'a', 'al', 'con', 'por', 'para', 'o', 'u']);

/** Muestra en formato título los nombres que el dataset trae en MAYÚSCULAS ("PARQUE DE LOS PATRICIOS" → "Parque de los Patricios"). */
export function nombrePropio(texto: string): string {
  if (texto !== texto.toUpperCase()) return texto; // ya viene con mayúsculas y minúsculas
  return texto.toLowerCase().split(' ').map((p, i) =>
    i > 0 && MINUSCULAS.has(p) ? p : p.replace(/^(\p{L})/u, (c) => c.toUpperCase())).join(' ');
}

export function formatearFecha(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export const s = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: 18, paddingBottom: 40 },
  titulo: { fontSize: 26, fontFamily: fuentes.titulo, color: colores.texto, marginBottom: 4, letterSpacing: -0.3 },
  tituloSeccion: { fontSize: 24, fontFamily: fuentes.titulo, color: colores.texto, letterSpacing: -0.3 },
  subtitulo: { fontSize: 19, fontFamily: fuentes.titulo, color: colores.texto, marginTop: 20, marginBottom: 10 },
  sobretitulo: { fontSize: 10, fontFamily: fuentes.extra, color: colores.suave, letterSpacing: 1.6, textTransform: 'uppercase', marginBottom: 2 },
  suave: { color: colores.suave, fontSize: 13, fontFamily: fuentes.medio },
  boton: { paddingVertical: 14, paddingHorizontal: 18, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  botonTexto: { fontFamily: fuentes.negrita, fontSize: 15 },
  etiqueta: { fontSize: 12, fontFamily: fuentes.negrita, color: colores.suave, marginBottom: 6, letterSpacing: 0.3 },
  input: {
    borderWidth: 1.5, borderColor: colores.borde, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 15, backgroundColor: colores.blanco, color: colores.texto, fontFamily: fuentes.medio,
  },
  tarjeta: {
    backgroundColor: colores.blanco, borderRadius: 20, padding: 14, marginBottom: 12, ...sombra,
  },
  chip: {
    flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1.5, borderRadius: 999,
    paddingHorizontal: 13, paddingVertical: 8, marginRight: 8, marginBottom: 8,
  },
  estado: { padding: 28, alignItems: 'center' },
  filaBotones: { flexDirection: 'row', gap: 10, marginTop: 10 },
});
