import msal
import requests
import pandas as pd
from io import BytesIO

## Prueba de implementación ##

# Configuración de la aplicación registrada
client_id = '74d020aa-8b8a-449d-98ae-f6cdbda02dac'
client_secret = '7a1673b3-a758-47e8-817d-6f161b8036e1'
tenant_id = 'f8cdef31-a31e-4b4a-93e4-5f571e91255a'
authority = f'https://login.microsoftonline.com/{tenant_id}'
redirect_uri = 'http://localhost'

# URL del archivo de Excel en OneDrive (ajústala según sea necesario)
file_url = 'https://1drv.ms/x/s!Avakh3YJalX_qXXLsH9n0SiPt2a6?e=nQGL0y'
file_content_url = file_url + ':/content'

# Iniciar la aplicación MSAL
app = msal.ConfidentialClientApplication(
    client_id,
    authority=authority,
    client_credential=client_secret,
)

# Solicitar un token de acceso
scopes = ['https://graph.microsoft.com/.default']
result = app.acquire_token_silent(scopes, account=None)

if not result:
    print("No cached token found, prompting for credentials.")
    result = app.acquire_token_for_client(scopes=scopes)

if 'access_token' in result:
    access_token = result['access_token']
else:
    raise Exception("Could not obtain access token")

# Verificar la última fecha de modificación del archivo
headers = {'Authorization': f'Bearer {access_token}'}
metadata_response = requests.get(file_url, headers=headers)
metadata_response.raise_for_status()
metadata = metadata_response.json()

# Obtener la última fecha de modificación del archivo
last_modified_time = metadata['lastModifiedDateTime']

# Leer la última fecha de modificación almacenada localmente
try:
    with open('last_modified_time.txt', 'r') as f:
        stored_last_modified_time = f.read().strip()
except FileNotFoundError:
    stored_last_modified_time = None

# Comparar las fechas y descargar el archivo si ha cambiado
if stored_last_modified_time != last_modified_time:
    print("El archivo ha cambiado, descargando...")
    
    # Descargar el archivo de Excel
    response = requests.get(file_content_url, headers=headers)
    response.raise_for_status()

    # Leer el archivo de Excel en un DataFrame de pandas
    excel_data = pd.read_excel(BytesIO(response.content))

    # Actualizar la última fecha de modificación almacenada localmente
    with open('last_modified_time.txt', 'w') as f:
        f.write(last_modified_time)

    # Mostrar el DataFrame para verificar que se ha leído correctamente
    print(excel_data)
else:
    print("El archivo no ha cambiado, no es necesario descargarlo.")
