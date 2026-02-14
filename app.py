import os
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
# Configuración de seguridad para sesiones en Render
app.secret_key = 'mauro_pilates_2026'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Configuración de la base de datos
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
        # Usuario y contraseña por defecto
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin123':
            session.clear() # Limpiamos sesión previa
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

# --- RUTAS DE ALUMNOS ---
@app.route('/alumnos')
@login_required
def alumnos():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alumnos ORDER BY nombre ASC")
    alumnos = cur.fetchall()
    conn.close()
    return render_template('alumnos.html', alumnos=alumnos)

@app.route('/agregar_alumno', methods=['POST'])
@login_required
def agregar_alumno():
    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono')
    conn = conectar()
    cur = conn.cursor()
    cur.execute("INSERT INTO alumnos (nombre, telefono) VALUES (%s, %s)", (nombre, telefono))
    conn.commit()
    conn.close()
    return redirect(url_for('alumnos'))

# --- RUTAS DE FACTURACIÓN ---
@app.route('/facturacion')
@login_required
def facturacion():
    conn = conectar()
    cur = conn.cursor()
    # Traemos pagos uniendo con la tabla alumnos para tener el nombre
    cur.execute("""
        SELECT p.*, a.nombre as alumno_nombre 
        FROM pagos p 
        JOIN alumnos a ON p.alumno_id = a.id 
        ORDER BY p.fecha DESC
    """)
    pagos = cur.fetchall()
    cur.execute("SELECT id, nombre FROM alumnos ORDER BY nombre ASC")
    alumnos = cur.fetchall()
    conn.close()
    return render_template('facturacion.html', pagos=pagos, alumnos=alumnos)

@app.route('/registrar_pago', methods=['POST'])
@login_required
def registrar_pago():
    alumno_id = request.form.get('alumno_id')
    monto = request.form.get('monto')
    concepto = request.form.get('concepto')
    estado = request.form.get('estado')
    
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagos (alumno_id, monto, concepto, estado, fecha) 
        VALUES (%s, %s, %s, %s, CURRENT_DATE)
    """, (alumno_id, monto, concepto, estado))
    conn.commit()
    conn.close()
    return redirect(url_for('facturacion'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)