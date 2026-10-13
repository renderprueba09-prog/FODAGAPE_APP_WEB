import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

# Configuración de carpeta para subida de fotos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurar que la carpeta de subidas exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tucorreo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu_contraseña_de_aplicacion'
app.config['MAIL_DEFAULT_SENDER'] = 'tucorreo@gmail.com'

mail = Mail(app)
DATABASE = 'database.db'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            mensaje TEXT NOT NULL
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS donaciones_dinero (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            monto TEXT NOT NULL,
            operacion TEXT NOT NULL
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            icono TEXT NOT NULL
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS testimonios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autor TEXT NOT NULL,
            rol TEXT NOT NULL,
            testimonio TEXT NOT NULL
        )''')
        # Tabla nueva para la Galería de Fotos
        db.execute('''CREATE TABLE IF NOT EXISTS galeria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            filename TEXT NOT NULL
        )''')

        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM configuracion")
        if cursor.fetchone()[0] == 0:
            defaults = {
                "hero_titulo": "Transformamos vidas con propósito y solidaridad",
                "hero_subtitulo": "Impulsamos el desarrollo comunitario en Cajamarca a través de programas de apoyo social, educación y asistencia humanitaria.",
                "frase_destacada": "Cada acción desinteresada tiene el poder de restaurar la esperanza.",
                "meta_recaudacion": "5000",
                "actual_recaudacion": "3400"
            }
            for k, v in defaults.items():
                cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (k, v))
        
        cursor.execute("SELECT COUNT(*) FROM proyectos")
        if cursor.fetchone()[0] == 0:
            db.execute("INSERT INTO proyectos (titulo, categoria, descripcion, icono) VALUES (?, ?, ?, ?)",
                       ("Apoyo Escolar Comunitario", "Educación", "Entrega de útiles y refuerzo académico para niños de zonas rurales.", "📚"))
            db.execute("INSERT INTO proyectos (titulo, categoria, descripcion, icono) VALUES (?, ?, ?, ?)",
                       ("Kits de Ayuda Humanitaria", "Social", "Distribución de alimentos de primera necesidad a familias vulnerables.", "🥫"))

        cursor.execute("SELECT COUNT(*) FROM testimonios")
        if cursor.fetchone()[0] == 0:
            db.execute("INSERT INTO testimonios (autor, rol, testimonio) VALUES (?, ?, ?)",
                       ("Rosa Sánchez", "Madre de familia beneficiaria", "Gracias al apoyo de la fundación, mis hijos pudieron recibir sus útiles escolares a tiempo para el año lectivo."))
        db.commit()

init_db()

def get_config():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT clave, valor FROM configuracion")
    return {row['clave']: row['valor'] for row in cursor.fetchall()}

@app.route('/')
def home():
    config = get_config()
    db = get_db()
    testimonios = db.execute("SELECT * FROM testimonios").fetchall()
    galeria = db.execute("SELECT * FROM galeria LIMIT 6").fetchall()
    return render_template('index.html', config=config, testimonios=testimonios, galeria=galeria)

@app.route('/proyectos')
def proyectos():
    db = get_db()
    lista_proyectos = db.execute("SELECT * FROM proyectos").fetchall()
    return render_template('proyectos.html', proyectos=lista_proyectos)

@app.route('/nosotros')
def nosotros():
    config = get_config()
    db = get_db()
    galeria = db.execute("SELECT * FROM galeria").fetchall()
    return render_template('nosotros.html', config=config, galeria=galeria)

@app.route('/donaciones')
def donaciones():
    config = get_config()
    return render_template('donaciones.html', config=config)

@app.route('/donacion-dinero', methods=['GET', 'POST'])
def donacion_dinero():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        monto = request.form.get('monto')
        operacion = request.form.get('operacion')

        db = get_db()
        db.execute("INSERT INTO donaciones_dinero (nombre, email, monto, operacion) VALUES (?, ?, ?, ?)",
                   (nombre, email, monto, operacion))
        db.commit()

        try:
            msg = Message('Confirmación de Donación - Fudagape', recipients=[email])
            msg.body = f"Hola {nombre},\n\nHemos recibido la notificación de tu donación por S/. {monto}. Código de operación: {operacion}.\n\n¡Muchas gracias por tu generosidad!"
            mail.send(msg)
        except Exception as e:
            print("Error al enviar correo:", e)

        return redirect(url_for('donacion_dinero', enviado=True))
    
    enviado = request.args.get('enviado', False)
    return render_template('donacion_dinero.html', enviado=enviado)

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        mensaje = request.form.get('mensaje')

        db = get_db()
        db.execute("INSERT INTO mensajes (nombre, email, mensaje) VALUES (?, ?, ?)",
                   (nombre, email, mensaje))
        db.commit()

        try:
            msg = Message('Mensaje Recibido - Fundación Fudagape', recipients=[email])
            msg.body = f"Hola {nombre},\n\nHemos recibido tu mensaje y nos pondremos en contacto contigo muy pronto.\n\nAtentamente,\nEquipo Fudagape"
            mail.send(msg)
        except Exception as e:
            print("Error al enviar correo:", e)

        return redirect(url_for('contacto', enviado=True))
    
    enviado = request.args.get('enviado', False)
    return render_template('contacto.html', enviado=enviado)

@app.route('/dashboard')
def dashboard():
    db = get_db()
    mensajes = db.execute("SELECT * FROM mensajes").fetchall()
    donaciones = db.execute("SELECT * FROM donaciones_dinero").fetchall()
    lista_proyectos = db.execute("SELECT * FROM proyectos").fetchall()
    testimonios = db.execute("SELECT * FROM testimonios").fetchall()
    galeria = db.execute("SELECT * FROM galeria").fetchall()
    config = get_config()
    return render_template('dashboard.html', mensajes=mensajes, donaciones=donaciones, proyectos=lista_proyectos, testimonios=testimonios, galeria=galeria, config=config)

@app.route('/dashboard/actualizar-config', methods=['POST'])
def actualizar_config():
    db = get_db()
    for clave, valor in request.form.items():
        db.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
    db.commit()
    return redirect(url_for('dashboard'))

# CRUD de Proyectos
@app.route('/dashboard/proyecto/agregar', methods=['POST'])
def agregar_proyecto():
    titulo = request.form.get('titulo')
    categoria = request.form.get('categoria')
    descripcion = request.form.get('descripcion')
    icono = request.form.get('icono')

    db = get_db()
    db.execute("INSERT INTO proyectos (titulo, categoria, descripcion, icono) VALUES (?, ?, ?, ?)",
               (titulo, categoria, descripcion, icono))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard/proyecto/eliminar/<int:id>', methods=['POST'])
def eliminar_proyecto(id):
    db = get_db()
    db.execute("DELETE FROM proyectos WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard'))

# CRUD de Testimonios
@app.route('/dashboard/testimonio/agregar', methods=['POST'])
def agregar_testimonio():
    autor = request.form.get('autor')
    rol = request.form.get('rol')
    testimonio = request.form.get('testimonio')

    db = get_db()
    db.execute("INSERT INTO testimonios (autor, rol, testimonio) VALUES (?, ?, ?)",
               (autor, rol, testimonio))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard/testimonio/eliminar/<int:id>', methods=['POST'])
def eliminar_testimonio(id):
    db = get_db()
    db.execute("DELETE FROM testimonios WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard'))

# CRUD de Galería de Fotos
@app.route('/dashboard/galeria/agregar', methods=['POST'])
def agregar_foto():
    titulo = request.form.get('titulo')
    file = request.files.get('foto')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db = get_db()
        db.execute("INSERT INTO galeria (titulo, filename) VALUES (?, ?)", (titulo, filename))
        db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard/galeria/eliminar/<int:id>', methods=['POST'])
def eliminar_foto(id):
    db = get_db()
    foto = db.execute("SELECT filename FROM galeria WHERE id = ?", (id,)).fetchone()
    if foto:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], foto['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        db.execute("DELETE FROM galeria WHERE id = ?", (id,))
        db.commit()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
