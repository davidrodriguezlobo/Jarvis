from flask import Blueprint, request, render_template, flash, session, redirect, url_for
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from nodes.extensions import mysql

mod = Blueprint('login', __name__, template_folder='templates')

@mod.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        #Get Form Fields

        username = request.form['username']
        password_candidate = request.form['password']

        #Create Cursor

        cur = mysql.connection.cursor()

        #

        result = cur.execute("SELECT * FROM tbl_users WHERE username = %s", [username])

        if result > 0:
            #Get stored hash
            data = cur.fetchone()
            password = data['password']

            #compare passwords
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in')
                return redirect(url_for('fb.fb'))
            else:
                flash('Invalid Login')
                return render_template('login/login.html')
        
        else:
            flash('Username not Found')
            return render_template('login/login.html')
        #Close COnnection
        cur.close()
    return render_template('login/login.html')