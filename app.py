import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'mauro_pilates_2026'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

DATABASE_URL = os.environ.get('DATABASE_URL')

def conectar():
    uri = DATABASE_URL
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(uri, cursor_factory=RealDictCursor)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin123':
            session.clear()
            session['admin'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# --- ALUMNOS ---
@app.route('/alumnos')
@login_required
def alumnos():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY apellido ASC, nombre ASC")
    alumnos_data = cur.fetchall()
    conn.close()
    return render_template('alumnos.html', alumnos=alumnos_data)

@app.route('/agregar_alumno', methods=['POST'])
@login_required
def agregar_alumno():
    datos = (
        request.form.get('nombre'), request.form.get('apellido'),
        request.form.get('dni'), request.form.get('domicilio'),
        request.form.get('telefono'), request.form.get('contacto_emergencia'),
        request.form.get('fecha_nacimiento') or None,
        request.form.get('peso') or None, request.form.get('altura') or None,
        request.form.get('patologias_cirugias'), request.form.get('obra_social'),
        request.form.get('medico_cabecera'), request.form.get('observaciones')
    )
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alumnos (nombre, apellido, dni, domicilio, telefono, contacto_emergencia, 
        fecha_nacimiento, peso, altura, patologias_cirugias, obra_social, medico_cabecera, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, datos)
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

@app.route('/eliminar_alumno/<int:id>')
@login_required
def eliminar_alumno(id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM alumnos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

# --- AGENDA PERMANENTE ---
@app.route('/agenda')
@login_required
def agenda():
    fecha_str = request.args.get('fecha')
    fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d') if fecha_str else datetime.now()
    inicio_semana = (fecha_actual - timedelta(days=fecha_actual.weekday())).date()
    fin_semana = inicio_semana + timedelta(days=5)
    horarios_fijos = [f"{h:02d}:00" for h in range(8, 22)]
    
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, a.nombre, a.apellido FROM turnos t 
        JOIN alumnos a ON t.alumno_id = a.id 
        ORDER BY t.hora ASC
    """)
    turnos = cur.fetchall()
    cur.execute("SELECT id, nombre, apellido FROM alumnos ORDER BY apellido ASC")
    alumnos_list = cur.fetchall()
    conn.close()
    return render_template('agenda.html', turnos=turnos, alumnos=alumnos_list, 
                           inicio=inicio_semana, fin=fin_semana, 
                           horarios=horarios_fijos, timedelta=timedelta)

@app.route('/agregar_turno', methods=['POST'])
@login_required
def agregar_turno():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO turnos (alumno_id, dia_semana, hora, observaciones) VALUES (%s, %s, %s, %s)",
               (request.form.get('alumno_id'), request.form.get('dia_semana'), request.form.get('hora'), request.form.get('observaciones')))
    conn.commit()
    conn.close()
    return redirect(url_for('agenda', fecha=request.form.get('fecha_inicio')))

@app.route('/mover_turno', methods=['POST'])
@login_required
def mover_turno():
    data = request.json
    conn = conectar()
    cur = conn.cursor()
    cur.execute("UPDATE turnos SET dia_semana=%s WHERE id=%s", (data.get('dia_semana'), data.get('id')))
    conn.commit()
    conn.close()
    return jsonify(status="ok")

@app.route('/eliminar_turno/<int:id>')
@login_required
def eliminar_turno(id):
    fecha_ref = request.args.get('fecha_ref')
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM turnos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('agenda', fecha=fecha_ref))

# --- FACTURACIÓN ---
@app.route('/facturacion')
@login_required
def facturacion():
    mes_filtro = request.args.get('mes_filtro')
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, apellido FROM alumnos ORDER BY apellido ASC")
    alumnos_cobro = cur.fetchall()
    
    if mes_filtro and mes_filtro != "Todos":
        cur.execute("""
            SELECT p.*, a.nombre || ' ' || a.apellido as alumno_nombre 
            FROM pagos p JOIN alumnos a ON p.alumno_id = a.id 
            WHERE p.concepto LIKE %s ORDER BY p.fecha DESC
        """, (f"%{mes_filtro}%",))
    else:
        cur.execute("""
            SELECT p.*, a.nombre || ' ' || a.apellido as alumno_nombre 
            FROM pagos p JOIN alumnos a ON p.alumno_id = a.id 
            ORDER BY p.fecha DESC LIMIT 100
        """)
        
    pagos = cur.fetchall()
    conn.close()
    return render_template('facturacion.html', alumnos=alumnos_cobro, pagos=pagos, 
                           datetime=datetime, mes_seleccionado=mes_filtro)

@app.route('/registrar_pago', methods=['POST'])
@login_required
def registrar_pago():
    concepto_final = f"{request.form.get('concepto')} - {request.form.get('mes')}"
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagos (alumno_id, monto, concepto, estado, fecha) 
        VALUES (%s, %s, %s, 'Pagado', CURRENT_DATE)
    """, (request.form.get('alumno_id'), request.form.get('monto'), concepto_final))
    conn.commit()
    conn.close()
    return redirect(url_for('facturacion'))

@app.route('/eliminar_pago/<int:id>')
@login_required
def eliminar_pago(id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM pagos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('facturacion'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)