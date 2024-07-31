import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '34dajvkeayhoj587320pfb32')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///article.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
