import os, io, psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

app = Flask(__name__)
app.secret_key = "pilates-mauro-2026-final"

# URL de conexión de Supabase (La pegás en las variables de entorno de Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

def conectar():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def inicializar_db():
    conn = conectar(); cur = conn.cursor()
    # Tablas con sintaxis PostgreSQL (la que usa Supabase)
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, password TEXT)")
    cur.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (usuario, password) VALUES (%s, %s)", ('admin', generate_password_hash('admin123')))
    
    cur.execute("""CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, dni TEXT, fecha_nacimiento TEXT,
        domicilio TEXT, telefono TEXT, edad INTEGER, contacto_emergencia TEXT,
        peso TEXT, patologias_cirugias TEXT, medico_cabecera TEXT, obra_social TEXT,
        pago_al_dia INTEGER DEFAULT 0, activo INTEGER DEFAULT 1, modalidad_pago INTEGER DEFAULT 0
    );""")
    
    cur.execute("CREATE TABLE IF NOT EXISTS agenda (id SERIAL PRIMARY KEY, alumno_id INTEGER REFERENCES alumnos(id), fecha TEXT, hora INTEGER);")
    
    cur.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)")
    for clave, valor in [('valor_clase', '5000'), ('valor_mes', '18000')]:
        cur.execute("SELECT * FROM configuracion WHERE clave = %s", (clave,))
        if not cur.fetchone(): cur.execute("INSERT INTO configuracion (clave, valor) VALUES (%s, %s)", (clave, valor))
    conn.commit(); cur.close(); conn.close()

# Llamamos a inicializar solo si tenemos la URL
if DATABASE_URL:
    inicializar_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user, password = request.form.get("usuario"), request.form.get("password")
        conn = conectar(); cur = conn.cursor(); cur.execute("SELECT * FROM usuarios WHERE usuario = %s", (user,))
        u = cur.fetchone(); cur.close(); conn.close()
        if u and check_password_hash(u['password'], password):
            session['user_id'] = u['id']; return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/")
@login_required
def index():
    fecha_str = request.args.get('fecha')
    hoy = datetime.strptime(fecha_str, '%Y-%m-%d') if fecha_str else datetime.now()
    lunes = hoy - timedelta(days=hoy.weekday())
    dias = [{'db': (lunes + timedelta(days=i)).strftime('%Y-%m-%d'), 'visual': (lunes + timedelta(days=i)).strftime('%d/%m/%Y')} for i in range(5)]
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT agenda.id, agenda.fecha, agenda.hora, alumnos.nombre, alumnos.pago_al_dia, alumnos.id as a_id FROM agenda JOIN alumnos ON agenda.alumno_id = alumnos.id WHERE agenda.fecha BETWEEN %s AND %s", (dias[0]['db'], dias[-1]['db']))
    ins = cur.fetchall()
    grilla = {h: {d['db']: [] for d in dias} for h in [14,15,16,17,18,19,20]}
    for i in ins: grilla[i['hora']][i['fecha']].append(dict(i))
    cur.execute("SELECT * FROM alumnos WHERE activo = 1 ORDER BY nombre")
    alumnos = [dict(row) for row in cur.fetchall()]
    cur.close(); conn.close()
    return render_template("pilates.html", grilla=grilla, cabecera=[{'nombre': n, 'db': dias[i]['db'], 'visual': dias[i]['visual']} for i, n in enumerate(['Lunes','Martes','Miércoles','Jueves','Viernes'])], horas=[14,15,16,17,18,19,20], alumnos=alumnos, ant=(lunes-timedelta(days=7)).strftime('%Y-%m-%d'), sig=(lunes+timedelta(days=7)).strftime('%Y-%m-%d'), actual=dias[0]['visual'])

@app.route("/facturacion")
@login_required
def facturacion():
    mes_sel = int(request.args.get('mes', datetime.now().month))
    anio_sel = int(request.args.get('anio', datetime.now().year))
    conn = conectar(); cur = conn.cursor()
    cur.execute("SELECT valor FROM configuracion WHERE clave = 'valor_clase'"); v_clase = int(cur.fetchone()['valor'])
    cur.execute("SELECT valor FROM configuracion WHERE clave = 'valor_mes'"); v_mes = int(cur.fetchone()['valor'])
    primer_dia = datetime(anio_sel, mes_sel, 1).strftime('%Y-%m-%d')
    if mes_sel == 12: ultimo_dia = datetime(anio_sel + 1, 1, 1) - timedelta(days=1)
    else: ultimo_dia = datetime(anio_sel, mes_sel + 1, 1) - timedelta(days=1)
    f_fin = ultimo_dia.strftime('%Y-%m-%d')
    cur.execute(f"SELECT a.*, (SELECT COUNT(*) FROM agenda WHERE alumno_id = a.id AND fecha BETWEEN '{primer_dia}' AND '{f_fin}') as clases_totales FROM alumnos a WHERE a.activo = 1 ORDER BY a.nombre")
    alumnos = [dict(row) for row in cur.fetchall()]
    cur.close(); conn.close()
    return render_template("facturacion.html", alumnos=alumnos, valor_clase=v_clase, valor_mes=v_mes, mes_sel=mes_sel, anio_sel=anio_sel, meses_nombres=["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])

@app.route("/guardar-alumno", methods=["POST"])
@login_required
def guardar_alumno():
    f = request.form; conn = conectar(); cur = conn.cursor()
    datos = [f['nombre'], f.get('dni',''), f.get('fecha_nac',''), f.get('domicilio',''), f.get('tel',''), int(f.get('edad',0)), f.get('emergencia',''), f.get('peso',''), f.get('patologias',''), f.get('medico',''), f.get('obra_social','')]
    if f.get('id'): 
        datos.append(f['id'])
        cur.execute("UPDATE alumnos SET nombre=%s, dni=%s, fecha_nacimiento=%s, domicilio=%s, telefono=%s, edad=%s, contacto_emergencia=%s, peso=%s, patologias_cirugias=%s, medico_cabecera=%s, obra_social=%s WHERE id=%s", datos)
    else: 
        cur.execute("INSERT INTO alumnos (nombre, dni, fecha_nacimiento, domicilio, telefono, edad, contacto_emergencia, peso, patologias_cirugias, medico_cabecera, obra_social) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", datos)
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('index'))

@app.route("/actualizar-precios", methods=["POST"])
@login_required
def actualizar_precios():
    v_clase = request.form.get("valor_clase").replace(".", "").replace(",", "")
    v_mes = request.form.get("valor_mes").replace(".", "").replace(",", "")
    conn = conectar(); cur = conn.cursor()
    cur.execute("UPDATE configuracion SET valor = %s WHERE clave = 'valor_clase'", (v_clase,))
    cur.execute("UPDATE configuracion SET valor = %s WHERE clave = 'valor_mes'", (v_mes,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('facturacion'))

@app.route("/cambiar-modalidad/<int:id>/<int:actual>")
@login_required
def cambiar_modalidad(id, actual):
    conn = conectar(); cur = conn.cursor()
    nueva = 1 if actual == 0 else 0
    cur.execute("UPDATE alumnos SET modalidad_pago=%s WHERE id=%s", (nueva, id))
    conn.commit(); cur.close(); conn.close()
    return redirect(request.referrer)

@app.route("/cambiar-pago/<int:id>/<int:estado>")
@login_required
def cambiar_pago(id, estado):
    conn = conectar(); cur = conn.cursor()
    nuevo = 1 if estado == 0 else 0
    cur.execute("UPDATE alumnos SET pago_al_dia=%s WHERE id=%s", (nuevo, id))
    conn.commit(); cur.close(); conn.close()
    return redirect(request.referrer)

@app.route("/asignar-turno", methods=["POST"])
@login_required
def asignar_turno():
    conn = conectar(); cur = conn.cursor()
    cur.execute("INSERT INTO agenda (alumno_id, fecha, hora) VALUES (%s,%s,%s)", (request.form['alumno_id'], request.form['fecha'], request.form['hora']))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('index', fecha=request.form['fecha']))

@app.route("/mover-turno", methods=["POST"])
@login_required
def mover_turno():
    data = request.get_json(); conn = conectar(); cur = conn.cursor()
    cur.execute("UPDATE agenda SET fecha = %s, hora = %s WHERE id = %s", (data['fecha'], data['hora'], data['id']))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "success"})

@app.route("/quitar-turno/<int:id>")
@login_required
def quitar_turno(id):
    conn = conectar(); cur = conn.cursor(); cur.execute("DELETE FROM agenda WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return redirect(request.referrer)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)