// Ajustes: selector de motor, usuario actual, URL del backend y modo debug.

import { useState } from 'react';
import { ScrollView, Switch, Text, View } from 'react-native';

import { Selector } from '@/components/Selector';
import { avisar, Boton, Campo, Chip, colorMotor, colores, s, Tarjeta } from '@/components/ui';
import { mensajeError, useApi, useCarga } from '@/lib/api';
import { useConfig } from '@/lib/config';
import type { Motor, Pagina, Usuario } from '@/lib/tipos';

export default function Ajustes() {
  const cfg = useConfig();
  const api = useApi();
  const [url, setUrl] = useState(cfg.apiUrl);
  const [probando, setProbando] = useState(false);
  const usuarios = useCarga(() => api.get<Pagina<Usuario>>('/usuarios?limite=100'), []);

  const [nuevo, setNuevo] = useState({ nombre_usuario: '', nombre: '', email: '' });
  const [creando, setCreando] = useState(false);

  const probar = async () => {
    setProbando(true);
    cfg.cambiar({ apiUrl: url.trim() });
    try {
      const r = await fetch(`${url.trim().replace(/\/$/, '')}/motores`);
      const j = await r.json();
      avisar('Conexión OK', `Motores disponibles: ${j.data.disponibles.join(', ')}`);
    } catch (e) {
      avisar('No se pudo conectar', mensajeError(e));
    } finally {
      setProbando(false);
    }
  };

  const crearUsuario = async () => {
    setCreando(true);
    try {
      const u = await api.post<Usuario>('/usuarios', { ...nuevo, nombre_usuario: nuevo.nombre_usuario.trim().toLowerCase() });
      cfg.cambiar({ idUsuario: u.id });
      setNuevo({ nombre_usuario: '', nombre: '', email: '' });
      usuarios.recargar();
      avisar('Usuario creado', `Ahora sos @${u.nombre_usuario} (en ${cfg.motor === 'mysql' ? 'MySQL' : 'HBase'})`);
    } catch (e) {
      avisar('No se pudo crear', mensajeError(e));
    } finally {
      setCreando(false);
    }
  };

  return (
    <ScrollView style={s.pantalla} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
      <Text style={s.subtitulo}>Motor de base de datos</Text>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {(['mysql', 'hbase'] as Motor[]).map((m) => (
          <View key={m} style={{ flex: 1 }}>
            <Boton
              titulo={m === 'mysql' ? 'MySQL' : 'HBase'}
              variante={cfg.motor === m ? 'primario' : 'secundario'}
              onPress={() => cfg.cambiar({ motor: m })}
              estilo={cfg.motor === m ? { backgroundColor: colorMotor(m) } : { borderColor: colorMotor(m) }}
            />
          </View>
        ))}
      </View>
      <Text style={[s.suave, { marginTop: 6 }]}>
        Todas las pantallas usan el mismo backend: solo cambia la implementación de persistencia (header X-Motor).
      </Text>

      <Text style={s.subtitulo}>Usuario actual</Text>
      <Selector
        etiqueta={`Usuarios en ${cfg.motor === 'mysql' ? 'MySQL' : 'HBase'}`}
        opciones={(usuarios.datos?.items ?? []).map((u) => ({ id: u.id, etiqueta: `@${u.nombre_usuario}`, detalle: u.nombre }))}
        valor={cfg.idUsuario}
        onCambiar={(id) => cfg.cambiar({ idUsuario: id })}
        textoVacio="Ninguno"
      />
      {usuarios.error ? <Text style={{ color: colores.peligro }}>{usuarios.error}</Text> : null}

      <Tarjeta>
        <Text style={{ fontWeight: '700', color: colores.texto, marginBottom: 8 }}>Crear usuario</Text>
        <Campo etiqueta="Nombre de usuario" value={nuevo.nombre_usuario} autoCapitalize="none"
          onChangeText={(t) => setNuevo({ ...nuevo, nombre_usuario: t })} placeholder="ej. ana.garcia" />
        <Campo etiqueta="Nombre" value={nuevo.nombre} onChangeText={(t) => setNuevo({ ...nuevo, nombre: t })} />
        <Campo etiqueta="Email" value={nuevo.email} autoCapitalize="none" keyboardType="email-address"
          onChangeText={(t) => setNuevo({ ...nuevo, email: t })} />
        <Boton titulo="Crear" onPress={crearUsuario} cargando={creando}
          deshabilitado={!nuevo.nombre_usuario || !nuevo.nombre || !nuevo.email} />
      </Tarjeta>

      <Text style={s.subtitulo}>Backend</Text>
      <Campo etiqueta="URL" value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} />
      <Boton titulo="Guardar y probar conexión" variante="secundario" onPress={probar} cargando={probando} />

      <Text style={s.subtitulo}>Modo debug</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: colores.texto, flex: 1 }}>Mostrar las operaciones que se ejecutan en la base</Text>
        <Switch value={cfg.debug} onValueChange={(v) => cfg.cambiar({ debug: v })} />
      </View>
      <View style={{ flexDirection: 'row', marginTop: 12 }}>
        <Chip texto={`Motor: ${cfg.motor}`} activo color={colorMotor(cfg.motor)} />
        <Chip texto={cfg.idUsuario ? `Usuario #${cfg.idUsuario}` : 'Sin usuario'} />
      </View>
    </ScrollView>
  );
}
