import os
from flask import Flask, render_template, request, redirect, url_for, session
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

@app.route('/alumnos')
@login_required
def alumnos():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY apellido ASC, nombre ASC")
    alumnos = cur.fetchall()
    conn.close()
    return render_template('alumnos.html', alumnos=alumnos)

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

@app.route('/editar_alumno/<int:id>', methods=['POST'])
@login_required
def editar_alumno(id):
    datos = (
        request.form.get('nombre'), request.form.get('apellido'),
        request.form.get('dni'), request.form.get('domicilio'),
        request.form.get('telefono'), request.form.get('contacto_emergencia'),
        request.form.get('fecha_nacimiento') or None,
        request.form.get('peso') or None, request.form.get('altura') or None,
        request.form.get('patologias_cirugias'), request.form.get('obra_social'),
        request.form.get('medico_cabecera'), request.form.get('observaciones'),
        id
    )
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE alumnos SET nombre=%s, apellido=%s, dni=%s, domicilio=%s, telefono=%s, 
        contacto_emergencia=%s, fecha_nacimiento=%s, peso=%s, altura=%s, 
        patologias_cirugias=%s, obra_social=%s, medico_cabecera=%s, observaciones=%s
        WHERE id=%s
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

@app.route('/agenda')
@login_required
def agenda():
    fecha_str = request.args.get('fecha')
    fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d') if fecha_str else datetime.now()
    
    # Lunes de la semana actual
    inicio_semana = (fecha_actual - timedelta(days=fecha_actual.weekday())).date()
    fin_semana = inicio_semana + timedelta(days=5)
    
    horarios_fijos = [f"{h:02d}:00" for h in range(8, 22)]
    
    conn = conectar()
    cur = conn.cursor()
    # FILTRO: Solo turnos de esta semana específica
    cur.execute("""
        SELECT t.*, a.nombre || ' ' || a.apellido as alumno_nombre 
        FROM turnos t JOIN alumnos a ON t.alumno_id = a.id 
        WHERE t.fecha >= %s AND t.fecha <= %s
        ORDER BY t.hora
    """, (inicio_semana, fin_semana))
    turnos = cur.fetchall()
    
    cur.execute("SELECT id, nombre, apellido FROM alumnos ORDER BY apellido ASC")
    alumnos = cur.fetchall()
    conn.close()
    
    return render_template('agenda.html', turnos=turnos, alumnos=alumnos, 
                           inicio=inicio_semana, fin=fin_semana, 
                           horarios=horarios_fijos, timedelta=timedelta)

@app.route('/agregar_turno', methods=['POST'])
@login_required
def agregar_turno():
    # El usuario elige Día (Lunes, etc) y nosotros calculamos la fecha exacta de ese día en la semana actual
    dia_nombre = request.form.get('dia_semana')
    fecha_referencia = datetime.strptime(request.form.get('fecha_inicio'), '%Y-%m-%d')
    dias_map = {'Lunes':0, 'Martes':1, 'Miércoles':2, 'Jueves':3, 'Viernes':4, 'Sábado':5}
    
    fecha_final = fecha_referencia + timedelta(days=dias_map[dia_nombre])

    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO turnos (alumno_id, dia_semana, hora, clases_semanales, observaciones, fecha) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (request.form.get('alumno_id'), dia_nombre, request.form.get('hora'), 
          request.form.get('clases_semanales'), request.form.get('observaciones'), fecha_final))
    conn.commit()
    conn.close()
    return redirect(url_for('agenda', fecha=request.form.get('fecha_inicio')))

@app.route('/facturacion')
@login_required
def facturacion():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT p.*, a.nombre || ' ' || COALESCE(a.apellido, '') as alumno_nombre FROM pagos p JOIN alumnos a ON p.alumno_id = a.id ORDER BY p.fecha DESC")
    pagos = cur.fetchall()
    cur.execute("SELECT id, nombre, apellido FROM alumnos ORDER BY apellido ASC")
    alumnos = cur.fetchall()
    conn.close()
    return render_template('facturacion.html', pagos=pagos, alumnos=alumnos)

@app.route('/registrar_pago', methods=['POST'])
@login_required
def registrar_pago():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO pagos (alumno_id, monto, concepto, estado, fecha) VALUES (%s, %s, %s, %s, CURRENT_DATE)", 
               (request.form.get('alumno_id'), request.form.get('monto'), request.form.get('concepto'), request.form.get('estado')))
    conn.commit()
    conn.close()
    return redirect(url_for('facturacion'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)