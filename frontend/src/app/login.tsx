import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Text, View } from 'react-native';

import { avisar, Boton, Campo, colores, s } from '@/components/ui';
import { mensajeError, useApi } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Sesion } from '@/lib/tipos';

export default function Login() {
  const api = useApi();
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
    <KeyboardAvoidingView
      style={[s.pantalla, { justifyContent: 'center' }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={[s.contenido, { width: '100%', maxWidth: 440, alignSelf: 'center' }]}>
        <Text style={{ color: colores.primario, fontSize: 38, fontWeight: '900' }}>Pasaporte BA</Text>
        <Text style={[s.suave, { fontSize: 16, marginBottom: 28 }]}>Descubrí y registrá tus visitas por la Ciudad.</Text>
        <Campo etiqueta="Usuario o email" value={usuario} onChangeText={setUsuario}
          autoCapitalize="none" autoCorrect={false} />
        <Campo etiqueta="Contraseña" value={password} onChangeText={setPassword}
          secureTextEntry autoCapitalize="none" />
        <Boton titulo="Ingresar" onPress={ingresar} cargando={cargando}
          deshabilitado={!usuario.trim() || !password} />
        <Text style={[s.suave, { marginTop: 16, textAlign: 'center' }]}>Las cuentas son creadas por un administrador.</Text>
      </View>
    </KeyboardAvoidingView>
  );
}
