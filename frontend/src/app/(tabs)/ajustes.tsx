// Perfil, conexion y herramientas exclusivas del administrador.

import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, Switch, Text, View } from 'react-native';

import { avisar, Boton, Campo, Chip, colores, s, Tarjeta } from '@/components/ui';
import { mensajeError, useApi, useCarga } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Pagina, Usuario } from '@/lib/tipos';

export default function Ajustes() {
  const cfg = useConfig();
  const api = useApi();
  const [url, setUrl] = useState(cfg.apiUrl);
  const [probando, setProbando] = useState(false);
  const [nuevo, setNuevo] = useState({ nombre_usuario: '', nombre: '', email: '', password: '', rol: 'usuario' as 'usuario' | 'admin' });
  const [creando, setCreando] = useState(false);

  const usuarios = useCarga(
    async () => cfg.usuario?.rol === 'admin' ? api.get<Pagina<Usuario>>('/usuarios?limite=100') : null,
    [cfg.usuario?.rol],
  );

  const probar = async () => {
    setProbando(true);
    cfg.cambiar({ apiUrl: url.trim() });
    try {
      const r = await fetch(`${url.trim().replace(/\/$/, '')}/motores`);
      const j = await r.json();
      avisar('Conexión correcta', `Catálogo: ${j.data.datos_maestros.toUpperCase()} · Actividad: ${j.data.actividad.toUpperCase()}`);
    } catch (e) {
      avisar('No se pudo conectar', mensajeError(e));
    } finally {
      setProbando(false);
    }
  };

  const crearUsuario = async () => {
    setCreando(true);
    try {
      const u = await api.post<Usuario>('/usuarios', {
        ...nuevo,
        nombre_usuario: nuevo.nombre_usuario.trim().toLowerCase(),
        email: nuevo.email.trim().toLowerCase(),
        id_barrio: null,
      });
      setNuevo({ nombre_usuario: '', nombre: '', email: '', password: '', rol: 'usuario' });
      usuarios.recargar();
      avisar('Cuenta creada', `@${u.nombre_usuario} ya puede iniciar sesión.`);
    } catch (e) {
      avisar('No se pudo crear', mensajeError(e));
    } finally {
      setCreando(false);
    }
  };

  const salir = async () => {
    try { await api.post('/auth/logout', {}); } catch { /* se limpia igual */ }
    cfg.limpiarSesion();
  };

  return (
    <ScrollView style={s.pantalla} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
      <Tarjeta>
        <Text style={s.titulo}>{cfg.usuario?.nombre}</Text>
        <Text style={s.suave}>@{cfg.usuario?.nombre_usuario} · {cfg.usuario?.email}</Text>
        <View style={{ flexDirection: 'row', marginTop: 10 }}>
          <Chip texto={cfg.usuario?.rol === 'admin' ? 'Administrador' : 'Usuario'} activo />
        </View>
      </Tarjeta>

      <Boton titulo="Mis favoritos" variante="secundario" onPress={() => router.push('/favoritos')} />
      <Boton titulo="Mis sugerencias" variante="secundario" onPress={() => router.push('/sugerencias')} estilo={{ marginTop: 8 }} />

      {cfg.usuario?.rol === 'admin' && (
        <>
          <Text style={s.subtitulo}>Administración</Text>
          <Boton titulo="Revisar sugerencias" onPress={() => router.push('/admin/sugerencias')} />
          <Tarjeta>
            <Text style={{ fontWeight: '700', color: colores.texto, marginBottom: 8 }}>Crear una cuenta</Text>
            <Campo etiqueta="Nombre de usuario" value={nuevo.nombre_usuario} autoCapitalize="none"
              onChangeText={(t) => setNuevo({ ...nuevo, nombre_usuario: t })} />
            <Campo etiqueta="Nombre" value={nuevo.nombre} onChangeText={(t) => setNuevo({ ...nuevo, nombre: t })} />
            <Campo etiqueta="Email" value={nuevo.email} autoCapitalize="none" keyboardType="email-address"
              onChangeText={(t) => setNuevo({ ...nuevo, email: t })} />
            <Campo etiqueta="Contraseña inicial" value={nuevo.password} secureTextEntry
              onChangeText={(t) => setNuevo({ ...nuevo, password: t })} />
            <View style={s.filaBotones}>
              <Boton titulo="Usuario" variante={nuevo.rol === 'usuario' ? 'primario' : 'secundario'}
                estilo={{ flex: 1 }} onPress={() => setNuevo({ ...nuevo, rol: 'usuario' })} />
              <Boton titulo="Admin" variante={nuevo.rol === 'admin' ? 'primario' : 'secundario'}
                estilo={{ flex: 1 }} onPress={() => setNuevo({ ...nuevo, rol: 'admin' })} />
            </View>
            <Boton titulo="Crear cuenta" onPress={crearUsuario} cargando={creando}
              deshabilitado={!nuevo.nombre_usuario || !nuevo.nombre || !nuevo.email || nuevo.password.length < 8} />
          </Tarjeta>
          <Text style={s.suave}>{usuarios.datos?.items.length ?? 0} cuentas cargadas.</Text>
        </>
      )}

      <Text style={s.subtitulo}>Backend</Text>
      <Campo etiqueta="URL" value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} />
      <Boton titulo="Guardar y probar conexión" variante="secundario" onPress={probar} cargando={probando} />

      <Text style={s.subtitulo}>Diagnóstico</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: colores.texto, flex: 1 }}>Mostrar qué base resolvió cada operación</Text>
        <Switch value={cfg.debug} onValueChange={(v) => cfg.cambiar({ debug: v })} />
      </View>
      <Boton titulo="Cerrar sesión" variante="peligro" onPress={salir} estilo={{ marginTop: 24 }} />
    </ScrollView>
  );
}
