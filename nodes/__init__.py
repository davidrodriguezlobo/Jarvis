from flask import Flask
from nodes.extensions import mysql

app = Flask(__name__)

from nodes.login.routes import mod
from nodes.dashboard.routes import mod
from nodes.sentiment.routes import mod
from nodes.fb.routes import mod
app.register_blueprint(login.routes.mod)
app.register_blueprint(dashboard.routes.mod)
app.register_blueprint(sentiment.routes.mod)
app.register_blueprint(fb.routes.mod)


#MySQL Config

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'app'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#Initiate MySQL

mysql.init_app(app)
app.secret_key = 'super secret key'