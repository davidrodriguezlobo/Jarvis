from flask import Blueprint, render_template
from flask_mysqldb import MySQL
from nodes.extensions import mysql
import datetime, calendar

mod = Blueprint('dashboard', __name__, template_folder='templates', static_folder='../static')

@mod.route('/dashboard')
def dashboard():
    return render_template('dashboard/dashboard.html')