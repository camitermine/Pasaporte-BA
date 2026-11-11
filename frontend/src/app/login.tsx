import Ionicons from '@expo/vector-icons/Ionicons';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { avisar, Boton, Campo, colores, fuentes, s, Sobretitulo } from '@/components/ui';
import { mensajeError, useApi } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Sesion } from '@/lib/tipos';

export default function Login() {
  const api = useApi();
  const insets = useSafeAreaInsets();
  const { establecerSesion } = useConfig();
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [cargando, setCargando] = useState(false);

  const ingresar = async () => {
    setCargando(true);
    try {
      const sesion = await api.post<Sesion>('/auth/login', { usuario: usuario.trim().toLowerCase(), password });
      establecerSesion(sesion);
    } catch (e) {
      avisar('No se pudo ingresar', mensajeError(e));
    } finally {
      setCargando(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.pantalla} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1 }}>
        <LinearGradient colors={['#3A8A66', colores.primario, '#143A2A']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
          style={{ paddingTop: insets.top + 48, paddingHorizontal: 24, paddingBottom: 64, overflow: 'hidden' }}>
          <View style={{ position: 'absolute', right: -50, top: insets.top - 10, width: 220, height: 220, borderRadius: 110, borderWidth: 26, borderColor: 'rgba(255,255,255,0.07)' }} />
          <View style={{ position: 'absolute', right: 70, bottom: 30, width: 80, height: 80, borderRadius: 40, borderWidth: 9, borderColor: 'rgba(242,196,109,0.2)' }} />
          <View style={{
            width: 54, height: 60, borderRadius: 10, borderBottomLeftRadius: 18, borderBottomRightRadius: 18,
            backgroundColor: colores.blanco, alignItems: 'center', justifyContent: 'center', marginBottom: 22,
          }}>
            <Text style={{ color: colores.primario, fontFamily: fuentes.titulo, fontSize: 24, transform: [{ rotate: '-4deg' }] }}>BA</Text>
          </View>
          <Sobretitulo color={colores.dorado}>Tu ciudad,</Sobretitulo>
          <Text style={{ color: colores.blanco, fontFamily: fuentes.titulo, fontSize: 44, lineHeight: 48 }}>
            Pasaporte <Text style={{ fontFamily: fuentes.tituloItalica, color: colores.dorado }}>BA</Text>
          </Text>
          <Text style={{ color: 'rgba(255,255,255,0.85)', fontFamily: fuentes.medio, fontSize: 16, marginTop: 8, lineHeight: 22 }}>
            Descubrí la Ciudad, sumá sellos y registrá cada visita.
          </Text>
        </LinearGradient>

        <View style={{
          flex: 1, backgroundColor: colores.fondo, marginTop: -32, borderTopLeftRadius: 30, borderTopRightRadius: 30,
          padding: 24, paddingBottom: insets.bottom + 24,
        }}>
          <View style={{ width: '100%', maxWidth: 440, alignSelf: 'center' }}>
            <Text style={[s.titulo, { marginBottom: 18 }]}>Ingresá</Text>
            <Campo etiqueta="Usuario o email" value={usuario} onChangeText={setUsuario}
              autoCapitalize="none" autoCorrect={false} />
            <Campo etiqueta="Contraseña" value={password} onChangeText={setPassword}
              secureTextEntry autoCapitalize="none" />
            <Boton titulo="Ingresar" icono="arrow-forward" onPress={ingresar} cargando={cargando}
              deshabilitado={!usuario.trim() || !password} estilo={{ marginTop: 6 }} />
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 18 }}>
              <Ionicons name="shield-checkmark-outline" size={14} color={colores.suave} />
              <Text style={s.suave}>Las cuentas son creadas por un administrador.</Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
