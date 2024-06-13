import re
import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.security import generate_password_hash
from excel_app import excel_bp, search_data
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import firebase_admin
from firebase_admin import credentials, auth
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Configura Firebase
cred = credentials.Certificate(app.config['GOOGLE_APPLICATION_CREDENTIALS'])
firebase_admin.initialize_app(cred)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, uid, name, email):
        self.id = uid
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    try:
        user_record = auth.get_user(user_id)
        return User(user_record.uid, user_record.display_name, user_record.email)
    except firebase_admin.auth.UserNotFoundError:
        return None

# Registrar el blueprint
app.register_blueprint(excel_bp)

# Leer el archivo Excel y las hojas Rankings y Raw data
file_path = 'Scouting Data Base_Womens_Alvaro.xlsx'
datos_rankings = pd.read_excel(file_path, sheet_name='Rankings')
raw_data = pd.read_excel(file_path, sheet_name='Raw data')

# Asegurarse de que la columna 'Games' exista en 'Raw data'
if 'Games' not in raw_data.columns:
    raise ValueError("La columna 'Games' no existe en la hoja 'Raw data'")

# Añadir la columna 'Games' al DataFrame de Rankings
datos_rankings['Games'] = raw_data['Games']

# Asegurar que los nombres de las columnas sean únicos
def make_column_names_unique(columns):
    seen = {}
    for i, col in enumerate(columns):
        if col in seen:
            seen[col] += 1
            columns[i] = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
    return columns

datos_rankings.columns = make_column_names_unique(datos_rankings.columns.tolist())

@app.route('/')
@login_required
def index():
    query = request.args.get('query')
    search_results = search_data(query) if query else {'resultados': [], 'tipo_busqueda': ''}
    results = search_results.get('resultados', [])
    tipo_busqueda = search_results.get('tipo_busqueda', '')

    if tipo_busqueda == 'player' and results:
        if len(results) == 1:
            result = results[0]
            return render_template('index.html', results=[result], tipo_busqueda=tipo_busqueda, query=query)
        else:
            return render_template('index.html', results=results, tipo_busqueda=tipo_busqueda, query=query)
    else:
        return render_template('index.html', results=results, tipo_busqueda=tipo_busqueda)

@app.route('/rankings')
@login_required
def rankings():
    filters = {
        'rating_min': request.args.get('rating_min'),
        'rating_max': request.args.get('rating_max'),
        'games_played_min': request.args.get('games_played_min'),
        'games_played_max': request.args.get('games_played_max'),
        'goals_min': request.args.get('goals_min'),
        'goals_max': request.args.get('goals_max'),
        'assists_min': request.args.get('assists_min'),
        'assists_max': request.args.get('assists_max'),
        'player_of_the_match': request.args.get('player_of_the_match'),
        'team': request.args.get('team'),
        'league': request.args.get('league'),
        'tier': request.args.get('tier'),
        'gender': request.args.get('gender'),
        'hidden_gem': request.args.get('hidden_gem')
    }
    page = int(request.args.get('page', 1))

    # Convert min and max values to float if they exist
    for key in ['rating_min', 'rating_max', 'games_played_min', 'games_played_max', 'goals_min', 'goals_max', 'assists_min', 'assists_max', 'player_of_the_match']:
        if filters[key] is not None and filters[key] != '':
            try:
                filters[key] = float(filters[key])
            except ValueError:
                filters[key] = None

    filtered_results = filter_data(filters)

    # Paginación
    items_per_page = 15
    start = (page - 1) * items_per_page
    end = start + items_per_page
    paginated_results = filtered_results[start:end]

    total_pages = (len(filtered_results) + items_per_page - 1) // items_per_page

    # Pasar datos únicos a la plantilla
    teams = datos_rankings['Team'].unique()
    leagues = datos_rankings['League'].unique()

    return render_template('rankings.html', results=paginated_results, page=page, total_pages=total_pages, filters=filters, teams=teams, leagues=leagues)

def filter_data(filters):
    df = datos_rankings.copy()

    if filters['team']:
        df = df[df['Team'].str.contains(filters['team'], case=False, na=False)]
    if filters['league']:
        df = df[df['League'].str.contains(filters['league'], case=False, na=False)]
    if filters['tier']:
        if filters['tier'].isdigit():
            df = df[df['Tier'] == int(filters['tier'])]
        elif filters['tier'].lower() == 'youth':
            df = df[df['Tier'].str.contains('Youth', case=False, na=False)]
    if filters['gender']:
        df = df[df['Male/Female'].str.contains(filters['gender'], case=False, na=False)]
    if filters['hidden_gem']:
        if filters['hidden_gem'].lower() == 'yes':
            df = df[df['Hidden Gem'] == 1]
        elif filters['hidden_gem'].lower() == 'no':
            df = df[df['Hidden Gem'] == 0]

    for col, min_val, max_val in [
        ('RATING', filters['rating_min'], filters['rating_max']),
        ('Games', filters['games_played_min'], filters['games_played_max']),
        ('Goals', filters['goals_min'], filters['goals_max']),
        ('Assists', filters['assists_min'], filters['assists_max']),
        ('Player of the Match', filters['player_of_the_match'], filters['player_of_the_match'])
    ]:
        if min_val is not None and min_val != '':
            if col == 'RATING':
                min_val = min_val / 100
            df = df[df[col].astype(float) >= min_val]
        if max_val is not None and max_val != '':
            if col == 'RATING':
                max_val = max_val / 100
            df = df[df[col].astype(float) <= max_val]

    # Ordenar por Rating de mayor a menor
    df = df.sort_values(by='RATING', ascending=False)

    # Convertir RATING a número entero sin decimales ni símbolo de porcentaje
    df['RATING'] = (df['RATING'].astype(float) * 100).fillna(0).astype(int)

    # Convertir Games a entero sin decimales
    df['Games'] = df['Games'].astype(float).astype(int)

    return df.to_dict(orient='records')

@app.route('/validate_token', methods=['POST'])
def validate_token():
    data = request.json
    id_token = data.get('idToken')
    try:
        decoded_token = auth.verify_id_token(id_token)
        user_record = auth.get_user(decoded_token['uid'])
        user_obj = User(user_record.uid, user_record.display_name, user_record.email)
        login_user(user_obj)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error validating token: {e}")
        return jsonify({'success': False, 'message': 'Invalid token'}), 401

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/sign-up')
def sign_up():
    return render_template('sign_up.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/terms-conditions')
def terms_conditions():
    return render_template('terms_conditions.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        directory=os.path.join(app.root_path, 'static', 'img'),
        path='favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Función para validar la complejidad de la contraseña
def validate_password(password):
    min_length = 8
    if (len(password) < min_length or not re.search("[A-Z]", password) or
        not re.search("[a-z]", password) or not re.search("[0-9]", password) or
        not re.search("[!@#$%^&*(),.?\":{}|<>]", password)):
        return False
    return True

# Endpoint para manejar el registro de usuarios
@app.route('/api/sign-up', methods=['POST'])
def api_sign_up():
    data = request.json
    email = data['email']
    password = data['password']

    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters long and include uppercase, lowercase, number, and special character'}), 400

    hashed_password = generate_password_hash(password)
    # Aquí puedes almacenar email y hashed_password en tu base de datos
    # Ejemplo usando Firebase:
    try:
        user_record = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            display_name=email.split('@')[0],
        )
        # Podrías almacenar el hash de la contraseña en tu base de datos si necesitas hacer verificaciones locales
        return jsonify({'message': 'User registered successfully', 'uid': user_record.uid}), 200
    except firebase_admin.auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists'}), 400

if __name__ == '__main__':
    app.run(debug=True)
