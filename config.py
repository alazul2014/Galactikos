from dotenv import load_dotenv
import os

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
