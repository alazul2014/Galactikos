import pandas as pd
from flask import Blueprint, request, jsonify

excel_bp = Blueprint('excel_bp', __name__)

# Leer el archivo Excel y las hojas específicas
file_path = 'Scouting Data Base_Womens_Alvaro.xlsx'
datos_excel = pd.read_excel(file_path, sheet_name='Rankings')
raw_data = pd.read_excel(file_path, sheet_name='Raw data')

# Asegurarse de que la columna 'Games' exista en 'Raw data'
if 'Games' not in raw_data.columns:
    raise ValueError("La columna 'Games' no existe en la hoja 'Raw data'")

# Añadir la columna 'Games' al DataFrame principal si es necesario
datos_excel['Games'] = raw_data['Games']

# Lista de columnas que deseas convertir a porcentaje
columnas_a_convertir = ['% Games Player of the Match', '% Teams goals', '% Teams Assists', '% Teams G+A', '% Came as a sub',
                        '% Appeared', '% Captain', '% Teams Sin Bins', '% Teams Yellows', '% Teams Reds']

datos_excel['RATING'] = datos_excel['RATING'].apply(lambda x: f"{int(round(x * 100))}" if pd.notna(x) else x)


# Convertir las columnas a formato de porcentaje y redondear a enteros
for columna in columnas_a_convertir:
    if columna in datos_excel.columns:
        datos_excel[columna] = datos_excel[columna].apply(lambda x: f"{int(round(x * 100))}%" if pd.notna(x) else x)

# Formatear columnas para mostrar solo dos decimales
columnas_a_redondear = ['Goals P90', 'Assists  P90', 'G+A P90', 'Sin Bins P90']
for columna in columnas_a_redondear:
    if columna in datos_excel.columns:
        datos_excel[columna] = datos_excel[columna].apply(lambda x: f"{x:.2f}" if pd.notna(x) else x)
def search_data(query):
    if not query:
        return {'tipo_busqueda': '', 'resultados': []}

    if datos_excel['Player Name'].str.contains(query, case=False).any():
        resultados = datos_excel[datos_excel['Player Name'].str.contains(query, case=False)]
        tipo_busqueda = 'player'
    elif datos_excel['Team'].str.contains(query, case=False).any():
        resultados = datos_excel[datos_excel['Team'].str.contains(query, case=False)]
        tipo_busqueda = 'team'
    else:
        return {'tipo_busqueda': '', 'resultados': []}

    columnas_deseadas = [
        'Player Name', 'Team', 'League', 'Div', 'Tier', 'Goals', 'Started', 'Appeared',
        'Captain', 'Bench Used', 'Assists', 'Goals P90', 'G+A P90', 'Assists  P90',
        'Sin Bins', 'Yellows', 'Reds', 'Player of the Match', 'Oppo. Player of the Match',
        'Sin Bins P90', 'Yellows P90', 'Reds P90', '% Games Player of the Match', 'RATING',
        '% Teams goals', '% Teams Assists', '% Teams G+A', 'G+A P90', 'Yellows P90', 'Games',
        '% Came as a sub', '% Appeared', '% Captain', '% Teams Sin Bins', '% Teams Yellows',
        '% Teams Reds', 'Sin Bins P90', 'Hidden Gem', 'Male/Female', 'Total Games Player of the Match'
    ]

    resultados_seleccionados = resultados[columnas_deseadas]

    return {
        'tipo_busqueda': tipo_busqueda,
        'resultados': resultados_seleccionados.to_dict(orient='records')
    }

    
@excel_bp.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    results = search_data(query)
    return jsonify(results)
