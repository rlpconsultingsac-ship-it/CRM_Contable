import streamlit as st 
import pandas as pd
import re
import calendar
from datetime import datetime, date
from sqlalchemy import text

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILO
# ==========================================
st.set_page_config(page_title="Estudio Contable ERP v2", layout="wide", page_icon="💼")

# Evitar dolores de cabeza visuales con cabeceras de tablas antiguas
st.markdown("""
    <style>
    th { background-color: #f0f2f6 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN MAESTRA A SUPABASE
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"❌ Error crítico de conexión con Supabase: {e}")
    st.stop()

# ==========================================
# 3. AUTOMATIZACIÓN DE IGUALAS (VERSIÓN CLOUD)
# ==========================================
def ejecutar_automatizaciones_cloud():
    hoy = date.today()
    mes_actual = hoy.strftime('%Y-%m')
    
    # 1. Traer solo los clientes que tienen facturación automática y están activos
    df_c = conn.query("SELECT ruc, cliente, fecha_inicio, monto_mensual_fijo FROM clientes WHERE facturacion_automatica = true AND estado = 'Activo';", ttl="0")
    if df_c.empty:
        return

    # 2. Verificar qué conceptos de este mes ya existen en la base de datos para no duplicar
    concepto_mes = f"Servicio Contable Tributario - Periodo {mes_actual}"
    df_f_existentes = conn.query("SELECT ruc FROM facturas WHERE concepto = :concepto;", params={"concepto": concepto_mes}, ttl="0")
    rucs_ya_facturados = set(df_f_existentes["ruc"].astype(str).tolist()) if not df_f_existentes.empty else set()
    
    # 3. Procesar e insertar directo en Supabase las que falten
    cambio_f = False
    with conn.session as session:
        for _, cliente in df_c.iterrows():
            ruc_str = str(cliente["ruc"]).strip()
            if ruc_str in rucs_ya_facturados:
                continue # Ya fue facturado este mes
            
            try:
                # Conversión segura de fecha desde el formato string/date de Postgres
                f_inicio = pd.to_datetime(cliente["fecha_inicio"]).date()
            except:
                continue
                
            if hoy >= f_inicio or mes_actual == f_inicio.strftime('%Y-%m'):
                monto = float(cliente["monto_mensual_fijo"])
                if monto > 0:
                    ultimo_dia_mes = calendar.monthrange(hoy.year, hoy.month)[1]
                    vencimiento_str = f"{hoy.year}-{hoy.month:02d}-{ultimo_dia_mes:02d}"
                    emision_str = f"{hoy.year}-{hoy.month:02d}-01"
                    
                    session.execute(
                        text("""
                        INSERT INTO facturas (ruc, cliente, concepto, monto_original, saldo_pendiente, fecha_emision, fecha_vencimiento, estado, tipo_gasto)
                        VALUES (:ruc, :cliente, :concepto, :monto, :monto, :emision, :vencimiento, 'Pendiente', 'Iguala Mensual Automática');
                        """),
                        {
                            "ruc": ruc_str,
                            "cliente": str(cliente["cliente"]),
                            "concepto": concepto_mes,
                            "monto": monto,
                            "emision": emision_str,
                            "vencimiento": vencimiento_str
                        }
                    )
                    cambio_f = True
        if cambio_f:
            session.commit()

# Ejecutamos la facturación recurrente en la nube antes de cargar las vistas
ejecutar_automatizaciones_cloud()

# ==========================================
# 4. CARGA Y BLINDAJE DE DATOS GLOBALES
# ==========================================
try:
    df_clientes = conn.query("SELECT * FROM clientes ORDER BY cliente ASC;", ttl="0")
    df_facturas = conn.query("SELECT * FROM facturas ORDER BY id DESC;", ttl="0")
    df_cobros = conn.query("SELECT * FROM cobros ORDER BY id DESC;", ttl="0")
    df_config = conn.query("SELECT * FROM configuracion;", ttl="0")
except Exception as e:
    st.error(f"❌ Error al mapear las tablas en la nube. Verifica que existan en Supabase.")
    st.info(f"Detalle técnico: {e}")
    st.stop()

# Replicamos exactamente tu formateador e higienizador de tipos de datos local
if not df_clientes.empty:
    df_clientes["ruc"] = df_clientes["ruc"].astype(str).str.replace(r'\.0$', '', regex=True)
    df_clientes["telefono"] = df_clientes["telefono"].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
    for col in ["observaciones", "contacto", "email", "cliente"]:
        if col in df_clientes.columns:
            df_clientes[col] = df_clientes[col].fillna("").astype(str)

if not df_facturas.empty:
    df_facturas["ruc"] = df_facturas["ruc"].astype(str).str.replace(r'\.0$', '', regex=True)
    df_facturas["monto_original"] = df_facturas["monto_original"].astype(float)
    df_facturas["saldo_pendiente"] = df_facturas["saldo_pendiente"].astype(float)
    df_facturas["concepto"] = df_facturas["concepto"].fillna("").astype(str)
    df_facturas["cliente"] = df_facturas["cliente"].fillna("").astype(str)

if not df_cobros.empty:
    df_cobros["ruc"] = df_cobros["ruc"].astype(str).str.replace(r'\.0$', '', regex=True)
    df_cobros["importe_total"] = df_cobros["importe_total"].astype(float)

if not df_config.empty:
    df_config["parametro"] = df_config["parametro"].fillna("").astype(str)
    df_config["valor"] = df_config["valor"].fillna("").astype(str)

# ==========================================
# 5. MENÚ LATERAL ESTILIZADO (TUS NOMBRES ORIGINALES)
# ==========================================
with st.sidebar:
    st.markdown("### 🏢 Menú de Control")
    menu = st.sidebar.radio(
        "Selecciona un Módulo:",
        ["📊 Dashboard", "📋 Clientes", "💵 Facturación", "💸 Cobranzas", "📊 Estados de Cuenta", "⚙️ Mantenimiento"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("v2.2.0 • Cloud Ready & Multi-Rollback")

# ==========================================
# A partir de aquí continúan tus bloques condicionales:
# if menu == "📊 Dashboard":
# ...
# ==========================================

# ==========================================
# 📊 DASHBOARD (VERSIÓN SUPABASE)
# ==========================================
if menu == "📊 Dashboard":
    st.title("📊 Resumen Gerencial")
    st.markdown("Visualización del estado financiero actual de la cartera de clientes.")
    
    # 1. Conexión y lectura de datos en tiempo real desde la nube
    conn = st.connection("postgresql", type="sql")
    df_clientes = conn.query("SELECT ruc, cliente, telefono FROM clientes;", ttl="0")
    df_facturas = conn.query("SELECT monto_original, saldo_pendiente, ruc FROM facturas;", ttl="0")
    
    with st.container(border=True):
        if not df_facturas.empty:
            # Forzamos conversión a float por seguridad (evita conflictos con tipo Decimal de PostgreSQL)
            t_pend = float(df_facturas["saldo_pendiente"].sum())
            t_emitido = float(df_facturas["monto_original"].sum())
            t_cobrado = t_emitido - t_pend
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Facturado", f"S/. {t_emitido:,.2f}")
            c2.metric("✅ Total Cobrado", f"S/. {t_cobrado:,.2f}")
            c3.metric("🚨 Cartera por Cobrar (Deuda)", f"S/. {t_pend:,.2f}", delta=f"Pendiente", delta_color="inverse")
        else:
            st.info("No hay transacciones registradas actualmente en la base de datos.")
            
    st.markdown("---")
    st.subheader("🚦 Semáforo de Riesgo y Deudas Pendientes")
    
    # Filtrar únicamente las facturas que tengan deuda activa
    df_deudas = df_facturas[df_facturas["saldo_pendiente"] > 0].copy()
    
    if not df_deudas.empty:
        # Aseguramos formato numérico antes de agrupar
        df_deudas["saldo_pendiente"] = df_deudas["saldo_pendiente"].astype(float)
        
        # Agrupamos por RUC y sumamos las deudas
        resumen_deuda = df_deudas.groupby("ruc")["saldo_pendiente"].sum().reset_index()
        
        # Cruzamos con la tabla de clientes para traer el Nombre y Teléfono
        resumen_deuda = pd.merge(resumen_deuda, df_clientes, on="ruc", how="left")
        resumen_deuda = resumen_deuda.sort_values(by="saldo_pendiente", ascending=False)
        
        # Lógica del semáforo basada en montos
        def asignar_semaforo(monto):
            if monto >= 5000: return "🔴 Riesgo Alto"
            elif monto >= 1000: return "🟡 Riesgo Medio"
            else: return "🟢 Controlado"
                
        resumen_deuda["Estado"] = resumen_deuda["saldo_pendiente"].apply(asignar_semaforo)
        
        # Seleccionamos y renombramos las columnas con nombres limpios y estéticos para el usuario
        vista_final = resumen_deuda[["Estado", "cliente", "ruc", "telefono", "saldo_pendiente"]].copy()
        vista_final.columns = ["Estado", "Cliente", "RUC", "Teléfono", "Deuda Total (S/.)"]
        
        st.dataframe(vista_final, use_container_width=True, hide_index=True)
    else:
        st.success("✨ ¡Excelente! No hay facturas con saldos pendientes actualmente.")

# ==========================================
# 📋 GESTIÓN DE CLIENTES (VERSIÓN SUPABASE)
# ==========================================
elif menu == "📋 Clientes":
    st.title("📋 Gestión Maestro de Clientes")
    
    # 1. Inicializar la conexión y leer los datos en tiempo real desde la nube
    conn = st.connection("postgresql", type="sql")
    df_clientes = conn.query("SELECT * FROM clientes ORDER BY cliente ASC;", ttl="0")
    
    seleccion = None
    tab_vista, tab_form = st.tabs(["📂 Lista de Clientes Activos", "📝 Registrar / Editar Cliente"])
    
    with tab_vista:
        st.markdown("💡 *Selecciona la casilla izquierda de un cliente y ve a la pestaña **'Registrar / Editar Cliente'** para modificar sus datos.*")
        if df_clientes.empty:
            st.info("No hay clientes en el sistema.")
        else:
            tabla_interactiva = st.dataframe(
                df_clientes, 
                use_container_width=True, 
                selection_mode="single-row", 
                on_select="rerun",
                key="tabla_clientes_view"
            )
            filas_seleccionadas = tabla_interactiva.get("selection", {}).get("rows", [])
            if filas_seleccionadas:
                seleccion = filas_seleccionadas[0]
                
    with tab_form:
        if seleccion is not None:
            # Obtenemos la fila seleccionada usando iloc y su ID de la base de datos
            row_c = df_clientes.iloc[seleccion]
            id_cliente = int(row_c["id"])
            
            st.subheader(f"🔧 Modificando: {row_c['cliente']}")
            
            with st.form("f_ed_cli_tab"):
                col_e1, col_e2 = st.columns(2)
                ed_nom = col_e1.text_input("Razón Social / Nombre", value=str(row_c["cliente"]))
                ed_eml = col_e1.text_input("Correo Electrónico", value=str(row_c["email"]))
                tel_inicial = str(row_c["telefono"]).strip()
                ed_tel = col_e2.text_input("Teléfono Celular (WhatsApp)", value=tel_inicial)
                ed_con = col_e2.text_input("Persona de Contacto Interno", value=str(row_c["contacto"]))
                
                # PostgreSQL maneja las fechas nativamente, validamos por seguridad si viene como texto
                try:
                    if isinstance(row_c["fecha_inicio"], str):
                        val_f_ini = datetime.strptime(row_c["fecha_inicio"], '%Y-%m-%d').date()
                    else:
                        val_f_ini = row_c["fecha_inicio"]
                except:
                    val_f_ini = date.today()
                    
                ed_f_ini = col_e1.date_input("Fecha Inicio de Contrato", value=val_f_ini)
                
                # Control dinámico del índice del selectbox basado en el estado actual de la nube
                estado_actual = str(row_c["estado"])
                lista_estados = ["Activo", "Inactivo", "Suspendido"]
                idx_estado = lista_estados.index(estado_actual) if estado_actual in lista_estados else 0
                ed_est = col_e2.selectbox("Estado Operativo", lista_estados, index=idx_estado)
                
                st.markdown("---")
                col_e3, col_e4 = st.columns(2)
                ed_monto = col_e3.number_input("Monto Tarifa Fija Mensual (S/.)", value=float(row_c["monto_mensual_fijo"]))
                ed_auto = col_e4.checkbox("¿Activar Facturación Automática de Igualas?", value=bool(row_c["facturacion_automatica"]))
                ed_obs = st.text_area("Observaciones o Comentarios Internos", value=str(row_c["observaciones"]))
                
                b_act, b_elim = st.columns([1, 1])
                
                if b_act.form_submit_button("💾 Guardar Cambios"):
                    with conn.session as session:
                        session.execute(
                            text("""
                            UPDATE clientes SET 
                                cliente = :cliente,
                                email = :email,
                                telefono = :telefono,
                                contacto = :contacto,
                                fecha_inicio = :fecha_inicio,
                                estado = :estado,
                                monto_mensual_fijo = :monto,
                                facturacion_automatica = :fact_auto,
                                observaciones = :observaciones
                            WHERE id = :id
                            """),  # 👈 Enuelto en text()
                            {
                                "cliente": ed_nom,
                                "email": ed_eml,
                                "telefono": str(ed_tel).strip(),
                                "contacto": ed_con,
                                "fecha_inicio": ed_f_ini,
                                "estado": ed_est,
                                "monto": ed_monto,
                                "fact_auto": ed_auto,
                                "observaciones": ed_obs,
                                "id": id_cliente
                            }
                        )
                        session.commit()
                    st.success("¡Datos actualizados correctamente en la nube!")
                    st.rerun()
                    
                if b_elim.form_submit_button("🗑️ Dar de Baja / Eliminar Cliente"):
                    with conn.session as session:
                        session.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": id_cliente}) # 👈 Envuelto en text()
                        session.commit()
                    st.warning("Cliente eliminado permanentemente de la base de datos.")
                    st.rerun()
        else:
            st.subheader("➕ Registrar Nuevo Cliente en el Sistema")
            with st.form("f_nuevo_cli_tab", clear_on_submit=True):
                col_n1, col_n2 = st.columns(2)
                ruc = col_n1.text_input("Número de RUC *")
                nom = col_n1.text_input("Razón Social / Nombre Comercial *")
                eml = col_n2.text_input("Correo Electrónico Primario *")
                tel = col_n2.text_input("Teléfono Móvil (WhatsApp) *")
                
                con_n = col_n1.text_input("Persona de Contacto")
                f_ini_n = col_n2.date_input("Fecha de Inicio de Labores", value=date.today())
                
                st.markdown("---")
                col_n3, col_n4 = st.columns(2)
                monto = col_n3.number_input("Tarifa Mensual Pactada (S/.)", min_value=0.0)
                auto = col_n4.checkbox("Habilitar Generación Automática de Facturas Mensuales")
                est = col_n3.selectbox("Estado Inicial", ["Activo", "Inactivo"])
                obs_n = st.text_area("Notas Adicionales")
                
                if st.form_submit_button("🚀 Dar de Alta Cliente"):
                    if ruc and nom and eml and tel:
                        ruc_limpio = str(ruc).strip()
                        
                        # Validamos directo en la nube si el RUC ya existe (conn.query ya maneja text por dentro, no cambies este)
                        check_ruc = conn.query("SELECT ruc FROM clientes WHERE ruc = :ruc LIMIT 1;", params={"ruc": ruc_limpio}, ttl="0")
                        
                        if not check_ruc.empty:
                            st.error("El RUC ingresado ya se encuentra registrado.")
                        else:
                            with conn.session as session:
                                session.execute(
                                    text("""
                                    INSERT INTO clientes (ruc, cliente, email, telefono, contacto, fecha_inicio, estado, observaciones, monto_mensual_fijo, facturacion_automatica)
                                    VALUES (:ruc, :cliente, :email, :telefono, :contacto, :fecha_inicio, :estado, :observaciones, :monto, :fact_auto)
                                    """),  # 👈 Envuelto en text()
                                    {
                                        "ruc": ruc_limpio,
                                        "cliente": nom,
                                        "email": eml,
                                        "telefono": str(tel).strip(),
                                        "contacto": con_n,
                                        "fecha_inicio": f_ini_n,
                                        "estado": est,
                                        "observaciones": obs_n,
                                        "monto": monto,
                                        "fact_auto": auto
                                    }
                                )
                                session.commit()
                            st.success("¡Cliente registrado con éxito en Supabase!")
                            st.rerun()
                    else:
                        st.error("Por favor completa todos los campos obligatorios (*).")

# ==========================================
# 💵 FACTURACIÓN (VERSIÓN SUPABASE)
# ==========================================
elif menu == "💵 Facturación":
    st.header("💵 Control y Emisión de Comprobantes")
    
    # 1. Inicializar conexión y leer facturas y clientes en tiempo real
    conn = st.connection("postgresql", type="sql")
    df_facturas = conn.query("SELECT * FROM facturas ORDER BY id DESC;", ttl="0")
    df_clientes = conn.query("SELECT cliente, ruc FROM clientes WHERE estado = 'Activo' ORDER BY cliente ASC;", ttl="0")
    
    seleccion_f = None
    tab_f_vista, tab_f_form = st.tabs(["📂 Historial de Facturas Emitidas", "📝 Modificar / Emitir Manual"])
    
    with tab_f_vista:
        st.markdown("💡 *Selecciona una fila para ajustar o rectificar montos directamente.*")
        if df_facturas.empty:
            st.info("No se registran facturas emitidas.")
        else:
            tabla_fac_int = st.dataframe(
                df_facturas, 
                use_container_width=True, 
                selection_mode="single-row", 
                on_select="rerun", 
                key="tabla_fac_view"
            )
            filas_f = tabla_fac_int.get("selection", {}).get("rows", [])
            
            if filas_f:
                if filas_f[0] < len(df_facturas):
                    seleccion_f = filas_f[0]
                else:
                    seleccion_f = None
                
    with tab_f_form:
        if seleccion_f is not None and seleccion_f < len(df_facturas):
            # Obtener datos de la fila seleccionada usando iloc y su ID real de base de datos
            row_f = df_facturas.iloc[seleccion_f]
            id_factura = int(row_f["id"])
            st.subheader(f"🔧 Rectificar Comprobante #{id_factura}")
            
            with st.form("f_ed_fac_tab"):
                ed_con = st.text_input("Concepto / Glosa Comercial", value=row_f["concepto"])
                
                col_f1, col_f2 = st.columns(2)
                ed_monto = col_f1.number_input("Importe Original (S/.)", value=float(row_f["monto_original"]))
                ed_saldo = col_f2.number_input("Saldo Pendiente de Cobro (S/.)", value=float(row_f["saldo_pendiente"]))
                
                # Conversión segura de fechas de PostgreSQL a objetos date de Python
                try:
                    if isinstance(row_f["fecha_emision"], str):
                        f_em_val = datetime.strptime(row_f["fecha_emision"], '%Y-%m-%d').date()
                    else:
                        f_em_val = row_f["fecha_emision"]
                except:
                    f_em_val = date.today()
                    
                try:
                    if isinstance(row_f["fecha_vencimiento"], str):
                        f_venc_val = datetime.strptime(row_f["fecha_vencimiento"], '%Y-%m-%d').date()
                    else:
                        f_venc_val = row_f["fecha_vencimiento"]
                except:
                    f_venc_val = date.today()
                
                ed_f_em = col_f1.date_input("Fecha Emisión", value=f_em_val)
                ed_f_venc = col_f2.date_input("Fecha Vencimiento", value=f_venc_val)
                
                lista_gastos = ["Servicios Extraordinarios", "Refacturación de Gastos Incurridos (Reembolsable)", "Iguala Mensual Automática"]
                g_idx = lista_gastos.index(row_f["tipo_gasto"]) if row_f["tipo_gasto"] in lista_gastos else 0
                ed_tipo_g = col_f1.selectbox("Clasificación Interna", lista_gastos, index=g_idx)
                
                lista_estados = ["Pendiente", "Abonado", "Pagado"]
                est_actual = str(row_f["estado"])
                est_idx = lista_estados.index(est_actual) if est_actual in lista_estados else 0
                ed_est = col_f2.selectbox("Estado de Pago", lista_estados, index=est_idx)
                
                fb1, fb2 = st.columns(2)
                
                if fb1.form_submit_button("💾 Actualizar Factura"):
                    with conn.session as session:
                        session.execute(
                            text("""
                            UPDATE facturas SET
                                concepto = :concepto,
                                monto_original = :monto_original,
                                saldo_pendiente = :saldo_pendiente,
                                fecha_emision = :fecha_emision,
                                fecha_vencimiento = :fecha_vencimiento,
                                tipo_gasto = :tipo_gasto,
                                estado = :estado
                            WHERE id = :id
                            """),
                            {
                                "concepto": ed_con,
                                "monto_original": ed_monto,
                                "saldo_pendiente": ed_saldo,
                                "fecha_emision": ed_f_em,
                                "fecha_vencimiento": ed_f_venc,
                                "tipo_gasto": ed_tipo_g,
                                "estado": ed_est,
                                "id": id_factura
                            }
                        )
                        session.commit()
                    st.success("¡Comprobante modificado exitosamente en la nube!")
                    st.rerun()
                    
                if fb2.form_submit_button("🗑️ Eliminar Registro"):
                    with conn.session as session:
                        session.execute(text("DELETE FROM facturas WHERE id = :id"), {"id": id_factura})
                        session.commit()
                    st.warning("Factura eliminada físicamente de la base de datos.")
                    st.rerun()
        else:
            # Formulario de emisión manual extraordinario
            st.subheader("📝 Emitir Factura Manual Extraordinaria")
            if df_clientes.empty:
                st.warning("Debe registrar al menos un cliente antes de emitir facturas.")
            else:
                with st.form("f_nueva_fac_tab", clear_on_submit=True):
                    # Emparejamos usando las columnas en minúsculas obtenidas de Supabase
                    dict_cli = dict(zip(df_clientes["cliente"], df_clientes["ruc"]))
                    c_sel = st.selectbox("Seleccione el Cliente Adquiriente:", list(dict_cli.keys()))
                    concepto = st.text_input("Glosa o Concepto del Servicio *")
                    
                    col_fn1, col_fn2 = st.columns(2)
                    monto = col_fn1.number_input("Monto Total Neto (S/.) *", min_value=1.0)
                    tipo_g = col_fn2.selectbox("Categoría del Ingreso", ["Servicios Extraordinarios", "Refacturación de Gastos Incurridos (Reembolsable)"])
                    f_venc_n = col_fn1.date_input("Fecha Vencimiento del Pago", value=date.today())
                    
                    if st.form_submit_button("🚀 Emitir Comprobante"):
                        if concepto and monto > 0:
                            with conn.session as session:
                                session.execute(
                                    text("""
                                    INSERT INTO facturas (ruc, cliente, concepto, monto_original, saldo_pendiente, fecha_emision, fecha_vencimiento, estado, tipo_gasto)
                                    VALUES (:ruc, :cliente, :concepto, :monto_original, :saldo_pendiente, :fecha_emision, :fecha_vencimiento, :estado, :tipo_gasto)
                                    """),
                                    {
                                        "ruc": str(dict_cli[c_sel]),
                                        "cliente": c_sel,
                                        "concepto": concepto,
                                        "monto_original": monto,
                                        "saldo_pendiente": monto,  # Al crearse, el saldo pendiente es el total
                                        "fecha_emision": date.today(),
                                        "fecha_vencimiento": f_venc_n,
                                        "estado": "Pendiente",
                                        "tipo_gasto": tipo_g
                                    }
                                )
                                session.commit()
                            st.success("¡Factura manual guardada con éxito en Supabase!")
                            st.rerun()
                        else: 
                            st.error("Completa el concepto e importe.")
                            
# ==========================================
# 💸 COBRANZAS (VERSIÓN SUPABASE con Transacciones)
# ==========================================
elif menu == "💸 Cobranzas":
    st.title("💸 Registro de Cobros y Recibos")
    
    # 1. Leer datos frescos de Supabase
    conn = st.connection("postgresql", type="sql")
    df_clientes = conn.query("SELECT cliente, ruc FROM clientes WHERE estado = 'Activo' ORDER BY cliente ASC;", ttl="0")
    df_facturas = conn.query("SELECT * FROM facturas ORDER BY id DESC;", ttl="0")
    df_cobros = conn.query("SELECT * FROM cobros ORDER BY id DESC;", ttl="0")
    
    if df_clientes.empty or df_facturas.empty:
        st.info("No se registran deudas activas en el sistema.")
    else:
        with st.container(border=True):
            st.subheader("🔍 Localizar Deuda por Cliente")
            c_cobrar = st.selectbox("Seleccione un Cliente:", df_clientes["cliente"].tolist())
            
            # Obtener el RUC del cliente seleccionado
            ruc_c = df_clientes[df_clientes["cliente"] == c_cobrar]["ruc"].values[0]
            
            # Filtrar facturas pendientes directo del DataFrame de Supabase
            fac_pendientes = df_facturas[(df_facturas["ruc"] == str(ruc_c)) & (df_facturas["saldo_pendiente"] > 0)]
            
        if fac_pendientes.empty:
            st.success("🎉 ¡Excelente! Este cliente se encuentra totalmente al día con sus pagos.")
        else:
            with st.form("f_multi_pago_diseño"):
                st.markdown("##### 🧾 Selecciona las Facturas que el cliente está cancelando:")
                lista_checkboxes = []
                for _, fac in fac_pendientes.iterrows():
                    # Usamos el id en minúscula de la base de datos
                    id_fac_real = int(fac['id'])
                    chk = st.checkbox(
                        f"📄 ID #{id_fac_real} | {fac['concepto']} — Saldo: S/. {float(fac['saldo_pendiente']):.2f}", 
                        key=f"chk_v2_{id_fac_real}"
                    )
                    lista_checkboxes.append((id_fac_real, chk))
                
                st.markdown("---")
                st.markdown("##### 💳 Información del Depósito o Pago")
                colM1, colM2 = st.columns(2)
                monto_depositado = colM1.number_input("Monto TOTAL Recibido en Banco (S/.) *", min_value=0.01, step=10.0)
                medio_p = colM1.selectbox("Medio de Pago Utilizado", ["BCP", "Interbank", "BBVA", "Yape", "Plin", "Efectivo", "Otro"])
                f_pago = colM2.date_input("Fecha en que se recibió el Pago", value=date.today())
                ref_p = colM2.text_input("Número de Operación / Referencia")
                
                if st.form_submit_button("⚡ Registrar Ingreso en Caja"):
                    facturas_a_pagar = [id_f for id_f, chk_activo in lista_checkboxes if chk_activo]
                    if not facturas_a_pagar:
                        st.error("Debes marcar al menos una factura de la lista superior.")
                    else:
                        monto_restante = monto_depositado
                        ids_afectados = []
                        
                        # Iniciamos una transacción SQL segura
                        with conn.session as session:
                            for id_f in facturas_a_pagar:
                                if monto_restante <= 0: 
                                    break
                                
                                # Localizar la factura específica en el DataFrame actual
                                fila_factura = df_facturas[df_facturas["id"] == id_f].iloc[0]
                                saldo_actual_f = float(fila_factura["saldo_pendiente"])
                                
                                if monto_restante >= saldo_actual_f:
                                    clock_monto = saldo_actual_f
                                    monto_restante -= saldo_actual_f
                                    nuevo_saldo = 0.0
                                    nuevo_estado = "Pagado"
                                    ids_afectados.append(f"F{id_f}(S/.{clock_monto:.2f})")
                                else:
                                    nuevo_saldo = saldo_actual_f - monto_restante
                                    nuevo_estado = "Abonado"
                                    ids_afectados.append(f"F{id_f}(S/.{monto_restante:.2f})")
                                    monto_restante = 0.0
                                
                                # Actualizar saldo de la factura en Supabase
                                session.execute(
                                    text("""
                                    UPDATE facturas 
                                    SET saldo_pendiente = :saldo, estado = :estado 
                                    WHERE id = :id
                                    """),
                                    {"saldo": nuevo_saldo, "estado": nuevo_estado, "id": id_f}
                                )
                            
                            # Insertar el Recibo de Caja en la tabla 'cobros' (Postgres genera el ID automáticamente)
                            session.execute(
                                text("""
                                INSERT INTO cobros (detalle_facturas, ruc, cliente, importe_total, fecha_pago, medio_pago, referencia)
                                VALUES (:detalle, :ruc, :cliente, :importe, :fecha, :medio, :referencia)
                                """),
                                {
                                    "detalle": ", ".join(ids_afectados),
                                    "ruc": str(ruc_c),
                                    "cliente": c_cobrar,
                                    "importe": monto_depositado,
                                    "fecha": f_pago,
                                    "medio": medio_p,
                                    "referencia": ref_p
                                }
                            )
                            # Confirmar todos los cambios juntos
                            session.commit()
                            
                        st.success("¡Cobranza procesada y saldos actualizados en Supabase!")
                        st.rerun()

        st.markdown("---")
        st.subheader("📜 Historial Reciente de Recibos de Caja")
        if not df_cobros.empty:
            st.dataframe(df_cobros, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔄 Revertir Recibo de Caja / Anular Cobro")
        
        if not df_cobros.empty:
            st.caption("Selecciona un recibo de cobro del historial. El sistema desarmará los abonos y reintegrará los montos a los saldos pendientes de cada factura.")
            
            df_revertir_vista = df_cobros.copy()
            df_revertir_vista["Detalle_Vista"] = (
                "Recibo #" + df_revertir_vista["id"].astype(str) + 
                " | " + df_revertir_vista["cliente"].astype(str) + 
                " | Total: S/. " + df_revertir_vista["importe_total"].astype(str) +
                " | Facturas: [" + df_revertir_vista["detalle_facturas"].astype(str) + "]"
            )
            
            cobro_seleccionado = st.selectbox("Seleccione la operación a anular:", df_revertir_vista["Detalle_Vista"].tolist())
            
            if st.button("🚨 Revertir Recibo Seleccionado", use_container_width=True):
                id_cobro_real = int(cobro_seleccionado.split(" | ")[0].replace("Recibo #", "").strip())
                fila_cobro = df_cobros[df_cobros["id"] == id_cobro_real].iloc[0]
                detalle_facturas_str = str(fila_cobro["detalle_facturas"])
                
                # Tu excelente lógica analítica con regex para desarmar el string
                matches = re.findall(r"F(\d+)\(S/\.([\d.]+)\)", detalle_facturas_str)
                
                if matches:
                    with conn.session as session:
                        for id_f_str, monto_str in matches:
                            id_factura_target = int(id_f_str)
                            monto_restituir = float(monto_str)
                            
                            # Verificar si la factura existe en la base de datos
                            if id_factura_target in df_facturas["id"].values:
                                fila_fac = df_facturas[df_facturas["id"] == id_factura_target].iloc[0]
                                saldo_actual = float(fila_fac["saldo_pendiente"])
                                monto_original = float(fila_fac["monto_original"])
                                
                                nuevo_saldo = min(saldo_actual + monto_restituir, monto_original)
                                nuevo_estado = "Pendiente" if nuevo_saldo >= monto_original else "Abonado"
                                
                                # Restituir el saldo en la base de datos
                                session.execute(
                                    text("""
                                    UPDATE facturas 
                                    SET saldo_pendiente = :saldo, estado = :estado 
                                    WHERE id = :id
                                    """),
                                    {"saldo": nuevo_saldo, "estado": nuevo_estado, "id": id_factura_target}
                                )
                        
                        # Eliminar físicamente el recibo de cobros anulado
                        session.execute(text("DELETE FROM cobros WHERE id = :id"), {"id": id_cobro_real})
                        session.commit()
                        
                    st.success(f"✅ ¡Éxito! El Recibo #{id_cobro_real} fue anulado y las facturas recuperaron sus deudas originales.")
                    st.rerun()
                else:
                    st.error("No se pudo extraer el detalle analítico de facturas de este recibo.")
        else:
            st.info("No se registran recibos de cobro para revertir.")

# ==========================================
# 📊 ESTADOS DE CUENTA (VERSIÓN SUPABASE)
# ==========================================
elif menu == "📊 Estados de Cuenta":
    st.title("📊 Estados de Cuenta y Envío de Alertas")
    
    import urllib.parse
    from fpdf import FPDF
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    # 1. Conexión y lectura de datos en tiempo real de Supabase
    conn = st.connection("postgresql", type="sql")
    df_clientes = conn.query("SELECT * FROM clientes WHERE estado = 'Activo' ORDER BY cliente ASC;", ttl="0")
    df_facturas = conn.query("SELECT * FROM facturas ORDER BY id DESC;", ttl="0")
    df_config = conn.query("SELECT * FROM configuracion;", ttl="0")

    def generar_pdf_estado_cuenta(cliente, ruc, deuda_total, facturas_pendientes, cfg):
        def get_cfg(parametro, default=""):
            if cfg.empty: return default
            valor = cfg[cfg["parametro"] == parametro]["valor"].values
            return str(valor[0]).strip() if len(valor) > 0 and pd.notna(valor[0]) else default

        emisor_nombre = get_cfg("empresa_nombre", "MI EMPRESA S.A.C.")
        emisor_ruc = get_cfg("empresa_ruc", "20000000000")
        emisor_dir = get_cfg("empresa_direccion", "Dirección Fiscal")
        emisor_tel = get_cfg("empresa_telefono", "-")
        emisor_email = get_cfg("empresa_email", "-")
        emisor_bancos = get_cfg("empresa_bancos", "No se configuraron cuentas bancarias.")

        pdf = FPDF()
        pdf.add_page()
        
        try: pdf.image("logo.png", x=15, y=15, w=60)
        except: pass
        
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 6, emisor_nombre, ln=True, align="R")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"RUC: {emisor_ruc}", ln=True, align="R")
        pdf.cell(0, 5, f"Dirección: {emisor_dir}", ln=True, align="R")
        pdf.cell(0, 5, f"E-mail: {emisor_email}", ln=True, align="R")
        pdf.cell(0, 5, f"Tel: {emisor_tel}", ln=True, align="R")
        
        pdf.ln(12)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "ESTADO DE CUENTA", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, f"Fecha de Emisión: {date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(8)
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "DATOS DEL CLIENTE:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"Razón Social: {cliente}", ln=True)
        pdf.cell(0, 5, f"RUC: {ruc}", ln=True)
        pdf.ln(5)
        
        pdf.set_fill_color(235, 243, 250) 
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 9, f"   DEUDA TOTAL GENERAL VENCIDA: S/. {deuda_total:,.2f}", ln=True, fill=True) 
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(15, 7, "ID", border=1, align="C", fill=True)
        pdf.cell(95, 7, "Concepto / Servicio", border=1, fill=True)
        pdf.cell(35, 7, "Vencimiento", border=1, align="C", fill=True)
        pdf.cell(45, 7, "Saldo Pendiente", border=1, align="R", ln=True, fill=True)
        
        pdf.set_font("Helvetica", "", 9)
        for _, f in facturas_pendientes.iterrows():
            pdf.cell(15, 7, str(f["id"]), border=1, align="C")
            pdf.cell(95, 7, f" {str(f['concepto'])[:45]}", border=1)
            pdf.cell(35, 7, str(f["fecha_vencimiento"]), border=1, align="C")
            pdf.cell(45, 7, f"S/. {float(f['saldo_pendiente']):,.2f} ", border=1, align="R", ln=True)
            
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, "CUENTAS BANCARIAS AUTORIZADAS:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, emisor_bancos)
        
        return pdf

    def enviar_correo_estado_cuenta(email_destinatario, asunto, cuerpo, pdf_bytes, filename, cfg):
        def get_cfg_str(parametro):
            if cfg.empty: return ""
            row = cfg[cfg["parametro"] == parametro]
            if not row.empty and pd.notna(row["valor"].values[0]):
                return str(row["valor"].values[0]).strip()
            return ""

        smtp_servidor = get_cfg_str("smtp_servidor")
        smtp_puerto = get_cfg_str("smtp_puerto")
        smtp_usuario = get_cfg_str("smtp_correo")
        smtp_password = get_cfg_str("smtp_token")

        if not smtp_usuario or not smtp_password:
            return "Credenciales SMTP incompletas en la base de datos de configuración."

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_usuario
            msg['To'] = str(email_destinatario)
            msg['Subject'] = str(asunto)

            cuerpo_seguro = str(cuerpo) if pd.notna(cuerpo) else ""
            msg.attach(MIMEText(cuerpo_seguro, 'plain', 'utf-8'))

            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

            puerto = int(smtp_puerto) if str(smtp_puerto).isdigit() else 465
            if puerto == 465:
                server = smtplib.SMTP_SSL(smtp_servidor, puerto, timeout=10)
            else:
                server = smtplib.SMTP(smtp_servidor, puerto, timeout=10)
                server.starttls()

            server.login(smtp_usuario, smtp_password)
            server.sendmail(smtp_usuario, email_destinatario, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            return str(e)

    if df_clientes.empty:
        st.info("No hay clientes en el sistema.")
    else:
        st.subheader("📝 Generación de Alertas por Cliente")
        cli_sel_ec = st.selectbox("Seleccione el Cliente:", df_clientes["cliente"].tolist())
        
        fila_cli = df_clientes[df_clientes["cliente"] == cli_sel_ec].iloc[0]
        ruc_cli = str(fila_cli["ruc"])
        email_cli = str(fila_cli["email"])
        tel_cli = str(fila_cli["telefono"])
        contacto_cli = str(fila_cli["contacto"]) if pd.notna(fila_cli["contacto"]) and str(fila_cli["contacto"]).strip() else cli_sel_ec
        
        # Filtrado con columnas en minúsculas
        fac_pend_ec = df_facturas[(df_facturas["ruc"] == ruc_cli) & (df_facturas["saldo_pendiente"] > 0)]
        deuda_total_ec = fac_pend_ec["saldo_pendiente"].sum() if not fac_pend_ec.empty else 0.0
        
        st.metric(label=f"Balance Pendiente de {cli_sel_ec}", value=f"S/. {deuda_total_ec:,.2f}")
        
        if fac_pend_ec.empty:
            st.success("✨ El cliente está al día en sus obligaciones financieras.")
        else:
            # Estructurar tabla de vista previa limpia
            df_mostrar = fac_pend_ec[["id", "concepto", "fecha_vencimiento", "saldo_pendiente"]].copy()
            df_mostrar.columns = ["ID Factura", "Concepto", "Fecha Vencimiento", "Saldo Pendiente"]
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            
            lineas = [f"- ID #{f['id']}: {f['concepto']} (Vence: {f['fecha_vencimiento']}) -> Saldo: S/. {float(f['saldo_pendiente']):.2f}" for _, f in fac_pend_ec.iterrows()]
            txt_detalle = "\n".join(lineas)
            
            def get_cfg_main(parametro, default=""):
                if df_config.empty: return default
                val = df_config[df_config["parametro"] == parametro]["valor"].values
                return str(val[0]).strip() if len(val) > 0 and pd.notna(val[0]) else default
                
            p_mail = get_cfg_main("mail_plantilla", "Estimado cliente, regularizar deuda de S/. {monto}")
            p_ws = get_cfg_main("ws_plantilla", "Hola, regularizar deuda de S/. {monto}")
            
            cuerpo_mail_fmt = p_mail.replace("{cliente}", contacto_cli).replace("{monto}", f"{deuda_total_ec:,.2f}").replace("{detalle}", txt_detalle)
            cuerpo_ws_fmt = p_ws.replace("{cliente}", contacto_cli).replace("{monto}", f"{deuda_total_ec:,.2f}").replace("{detalle}", txt_detalle)
            
            pdf_generado = generar_pdf_estado_cuenta(cli_sel_ec, ruc_cli, deuda_total_ec, fac_pend_ec, df_config)
            
            try:
                pdf_res = pdf_generado.output(dest='S')
                pdf_bytes = pdf_res.encode('latin-1') if isinstance(pdf_res, str) else bytes(pdf_res)
            except Exception as e:
                pdf_bytes = bytes()
                st.error(f"Error al compilar PDF: {e}")
                
            col_acc1, col_acc2, col_acc3 = st.columns(3)
            
            col_acc1.download_button(
                label="📥 Descargar PDF Estado de Cuenta",
                data=pdf_bytes,
                file_name=f"Estado_Cuenta_{ruc_cli}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
            if col_acc2.button("📧 Enviar por Correo Electrónico", use_container_width=True):
                if not email_cli or "@" not in email_cli:
                    st.error("El cliente no cuenta con una dirección de E-mail válida.")
                else:
                    with st.spinner("Conectando con el servidor SMTP corporativo..."):
                        asunto_mail = f"Estado de Cuenta Pendiente - {cli_sel_ec}"
                        resultado = enviar_correo_estado_cuenta(email_cli, asunto_mail, cuerpo_mail_fmt, pdf_bytes, f"Estado_Cuenta_{ruc_cli}.pdf", df_config)
                        if resultado == True:
                            st.success(f"✅ ¡Correo enviado exitosamente a {email_cli}!")
                        else:
                            st.error(f"❌ Error al enviar correo: {resultado}")
                            
            texto_ws_encoded = urllib.parse.quote(cuerpo_ws_fmt)
            ws_url = f"https://api.whatsapp.com/send?phone={tel_cli}&text={texto_ws_encoded}"
            col_acc3.markdown(
                f'<a href="{ws_url}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">💬 Notificar por WhatsApp</button></a>', 
                unsafe_allow_html=True
            )

# ==========================================
# ⚙️ MANTENIMIENTO DEL SISTEMA (VERSIÓN SUPABASE)
# ==========================================
elif menu == "⚙️ Mantenimiento":
    st.title("⚙️ Mantenimiento del Sistema")
    st.markdown("Ajustes generales de la empresa emisora, textos de deudas y parámetros SMTP de salida.")
    
    # 1. Conexión y lectura en tiempo real desde Supabase
    conn = st.connection("postgresql", type="sql")
    df_config = conn.query("SELECT * FROM configuracion;", ttl="0")
    
    # Función auxiliar ultra-segura para extraer los valores actuales
    def get_val(p):
        if df_config.empty:
            return ""
        val = df_config[df_config["parametro"] == p]["valor"].values
        return str(val[0]).strip() if len(val) > 0 and pd.notna(val[0]) else ""

    tab_m1, tab_m2, tab_m3 = st.tabs(["🏢 Datos de la Empresa", "💬 Plantillas de Alertas", "📧 Servidor de Correo (SMTP)"])
    
    with tab_m1:
        with st.form("f_mant_empresa"):
            m_nom = st.text_input("Razón Social Emisora", value=get_val("empresa_nombre"))
            m_ruc = st.text_input("RUC de la Empresa", value=get_val("empresa_ruc"))
            m_dir = st.text_input("Dirección Fiscal", value=get_val("empresa_direccion"))
            m_tel = st.text_input("Teléfono Corporativo", value=get_val("empresa_telefono"))
            m_eml = st.text_input("Correo de Contacto", value=get_val("empresa_email"))
            m_ban = st.text_area("Cuentas Bancarias Disponibles", value=get_val("empresa_bancos"))
            
            if st.form_submit_button("💾 Guardar Datos de Empresa"):
                datos_empresa = {
                    "empresa_nombre": m_nom,
                    "empresa_ruc": m_ruc,
                    "empresa_direccion": m_dir,
                    "empresa_telefono": m_tel,
                    "empresa_email": m_eml,
                    "empresa_bancos": m_ban
                }
                
                # Guardado masivo y seguro usando transacciones con un "UPSERT" lógico
                with conn.session as session:
                    for param, valor in datos_empresa.items():
                        session.execute(
                            text("""
                            INSERT INTO configuracion (parametro, valor) 
                            VALUES (:param, :valor)
                            ON CONFLICT (parametro) 
                            DO UPDATE SET valor = EXCLUDED.valor;
                            """),
                            {"param": param, "valor": valor}
                        )
                    session.commit()
                st.success("✅ Datos corporativos actualizados en Supabase.")
                st.rerun()
                
    with tab_m2:
        with st.form("f_mant_plantillas"):
            st.caption("Comodines utilizables: {cliente}, {monto} y {detalle} (se auto-completarán solos).")
            m_wsp = st.text_area("Cuerpo del mensaje para WhatsApp", value=get_val("ws_plantilla"), height=130)
            m_mlp = st.text_area("Cuerpo del mensaje para Correo", value=get_val("mail_plantilla"), height=130)
            
            if st.form_submit_button("💾 Guardar Plantillas"):
                datos_plantillas = {
                    "ws_plantilla": m_wsp,
                    "mail_plantilla": m_mlp
                }
                
                with conn.session as session:
                    for param, valor in datos_plantillas.items():
                        session.execute(
                            text("""
                            INSERT INTO configuracion (parametro, valor) 
                            VALUES (:param, :valor)
                            ON CONFLICT (parametro) 
                            DO UPDATE SET valor = EXCLUDED.valor;
                            """),
                            {"param": param, "valor": valor}
                        )
                    session.commit()
                st.success("✅ Plantillas de mensajería guardadas en Supabase.")
                st.rerun()
                
    with tab_m3:
        with st.form("f_mant_smtp"):
            m_s_cor = st.text_input("Correo Remitente (SMTP Usuario)", value=get_val("smtp_correo"))
            m_s_tok = st.text_input("Token / Contraseña de Aplicación", value=get_val("smtp_token"), type="password")
            m_s_srv = st.text_input("Servidor de Salida SMTP", value=get_val("smtp_servidor"))
            m_s_pto = st.text_input("Puerto SMTP", value=get_val("smtp_puerto"))
            
            if st.form_submit_button("💾 Guardar Configuración SMTP"):
                datos_smtp = {
                    "smtp_correo": m_s_cor,
                    "smtp_token": m_s_tok,
                    "smtp_servidor": m_s_srv,
                    "smtp_puerto": m_s_pto
                }
                
                with conn.session as session:
                    for param, valor in datos_smtp.items():
                        session.execute(
                            text("""
                            INSERT INTO configuracion (parametro, valor) 
                            VALUES (:param, :valor)
                            ON CONFLICT (parametro) 
                            DO UPDATE SET valor = EXCLUDED.valor;
                            """),
                            {"param": param, "valor": valor}
                        )
                    session.commit()
                st.success("✅ Servidor SMTP vinculado en Supabase.")
                st.rerun()
