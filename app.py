import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'mauro_pilates_2026_pro_max'

# --- CONFIGURACIÓN DE LOGOS ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Max 2MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DATABASE_URL = os.environ.get('DATABASE_URL')

def conectar():
    uri = DATABASE_URL
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(uri, cursor_factory=RealDictCursor)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- SISTEMA DE ACCESO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))
        nombre_estudio = request.form.get('nombre_estudio')
        conn = conectar()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO usuarios (email, password, nombre_estudio) VALUES (%s, %s, %s)",
                       (email, password, nombre_estudio))
            conn.commit()
            return redirect(url_for('login'))
        except:
            return "El email ya está registrado."
        finally:
            conn.close()
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['nombre_estudio']
            session['user_logo'] = user['logo_url']
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        file = request.files.get('logo')
        nombre = request.form.get('nombre_estudio')
        conn = conectar()
        cur = conn.cursor()
        logo_url = session.get('user_logo')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"logo_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            logo_url = filename
        cur.execute("UPDATE usuarios SET nombre_estudio=%s, logo_url=%s WHERE id=%s",
                   (nombre, logo_url, session['user_id']))
        conn.commit()
        session['user_name'] = nombre
        session['user_logo'] = logo_url
        conn.close()
        return redirect(url_for('index'))
    return render_template('perfil.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# --- ALUMNOS (13 CAMPOS) ---
@app.route('/alumnos')
@login_required
def alumnos():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alumnos WHERE user_id = %s ORDER BY apellido ASC", (session['user_id'],))
    alumnos_data = cur.fetchall()
    conn.close()
    return render_template('alumnos.html', alumnos=alumnos_data)

@app.route('/agregar_alumno', methods=['POST'])
@login_required
def agregar_alumno():
    datos = (
        request.form.get('nombre'), request.form.get('apellido'), request.form.get('dni'),
        request.form.get('domicilio'), request.form.get('telefono'), request.form.get('contacto_emergencia'),
        request.form.get('fecha_nacimiento') or None, request.form.get('peso') or None,
        request.form.get('altura') or None, request.form.get('patologias_cirugias'),
        request.form.get('obra_social'), request.form.get('medico_cabecera'), 
        request.form.get('observaciones'), session['user_id']
    )
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""INSERT INTO alumnos (nombre, apellido, dni, domicilio, telefono, contacto_emergencia, 
                fecha_nacimiento, peso, altura, patologias_cirugias, obra_social, medico_cabecera, observaciones, user_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", datos)
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

@app.route('/editar_alumno/<int:id>', methods=['POST'])
@login_required
def editar_alumno(id):
    datos = (
        request.form.get('nombre'), request.form.get('apellido'), request.form.get('dni'),
        request.form.get('domicilio'), request.form.get('telefono'), request.form.get('contacto_emergencia'),
        request.form.get('fecha_nacimiento') or None, request.form.get('peso') or None,
        request.form.get('altura') or None, request.form.get('patologias_cirugias'),
        request.form.get('obra_social'), request.form.get('medico_cabecera'), 
        request.form.get('observaciones'), id, session['user_id']
    )
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""UPDATE alumnos SET nombre=%s, apellido=%s, dni=%s, domicilio=%s, telefono=%s, 
                contacto_emergencia=%s, fecha_nacimiento=%s, peso=%s, altura=%s, patologias_cirugias=%s, 
                obra_social=%s, medico_cabecera=%s, observaciones=%s WHERE id=%s AND user_id=%s""", datos)
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

@app.route('/eliminar_alumno/<int:id>')
@login_required
def eliminar_alumno(id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM alumnos WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

# --- AGENDA DUAL (L-V) ---
@app.route('/agenda')
@login_required
def agenda():
    fecha_str = request.args.get('fecha')
    fecha_actual = datetime.strptime(fecha_str, '%Y-%m-%d') if fecha_str else datetime.now()
    inicio_semana = (fecha_actual - timedelta(days=fecha_actual.weekday())).date()
    fin_semana = inicio_semana + timedelta(days=4)
    horarios_fijos = [f"{h:02d}:00" for h in range(8, 22)]
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""SELECT t.*, a.nombre, a.apellido FROM turnos t JOIN alumnos a ON t.alumno_id = a.id 
                WHERE t.user_id = %s ORDER BY t.hora ASC""", (session['user_id'],))
    turnos = cur.fetchall()
    cur.execute("SELECT id, nombre, apellido FROM alumnos WHERE user_id = %s ORDER BY apellido ASC", (session['user_id'],))
    alumnos_list = cur.fetchall()
    conn.close()
    return render_template('agenda.html', turnos=turnos, alumnos=alumnos_list, 
                           inicio=inicio_semana, fin=fin_semana, horarios=horarios_fijos, timedelta=timedelta)

@app.route('/agregar_turno', methods=['POST'])
@login_required
def agregar_turno():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO turnos (alumno_id, dia_semana, hora, user_id) VALUES (%s, %s, %s, %s)",
               (request.form.get('alumno_id'), request.form.get('dia_semana'), request.form.get('hora'), session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('agenda', fecha=request.form.get('fecha_inicio')))

@app.route('/eliminar_turno/<int:id>')
@login_required
def eliminar_turno(id):
    fecha_ref = request.args.get('fecha_ref')
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM turnos WHERE id = %s AND user_id = %s", (id, session['user_id']))
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
    cur.execute("SELECT id, nombre, apellido FROM alumnos WHERE user_id = %s ORDER BY apellido ASC", (session['user_id'],))
    alumnos_cobro = cur.fetchall()
    query = "SELECT p.*, a.nombre || ' ' || a.apellido as alumno_nombre FROM pagos p JOIN alumnos a ON p.alumno_id = a.id WHERE p.user_id = %s"
    params = [session['user_id']]
    if mes_filtro and mes_filtro != "Todos":
        query += " AND p.concepto LIKE %s"
        params.append(f"%{mes_filtro}%")
    query += " ORDER BY p.fecha DESC LIMIT 100"
    cur.execute(query, params)
    pagos = cur.fetchall()
    conn.close()
    return render_template('facturacion.html', alumnos=alumnos_cobro, pagos=pagos, datetime=datetime, mes_seleccionado=mes_filtro)

@app.route('/registrar_pago', methods=['POST'])
@login_required
def registrar_pago():
    concepto_final = f"{request.form.get('concepto')} - {request.form.get('mes')}"
    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO pagos (alumno_id, monto, concepto, estado, fecha, user_id) VALUES (%s, %s, %s, 'Pagado', CURRENT_DATE, %s)",
               (request.form.get('alumno_id'), request.form.get('monto'), concepto_final, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('facturacion'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)