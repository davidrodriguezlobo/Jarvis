from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import datetime
import json
import requests as rqst
from google.cloud import automl_v1beta1 as automl

app = Flask(__name__)

#MySQL Config

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'app'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#Initiate MySQL

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')


class RegisterForm(Form):
    name = StringField('Name', [validators.length(min=1, max=50)])
    username = StringField('Username', [validators.length(min=4, max=25)])
    email = StringField('Email', [validators.length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO tbl_users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        mysql.connection.commit()

        cur.close()

        flash('Gracias por registrarte!', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
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

                flash('You are now logged in', 'success')
                return redirect(url_for('menu'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)
        
        else:
            error = 'Username not Found'
            return render_template('login.html', error=error)
        #Close COnnection
        cur.close()
    return render_template('login.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')


#EXTRAER POSTS DE FB
@app.route('/posts')
def posts():

    #Token Temporal
    token = 'EAAIPgJKNjsgBAMMYFgAiY1wHJyIWzP1PK0cvmkGZBfN72McbiOEX8zOjbdlpYXwDKO3FwPZC1Amofl66zGcZCeRbaknaUPNQHQN6ZBPKpcnZCGWkH8SPHv16oudct6qB11sXQxuQFZBqt7oxE6NBeWZCzDpuxq8xrV6HeqEZAfyLjTinL2UnejXJVNkbvpxz8LJ2DC6zwcWItpZBoJjdycCvVEvZBLOUf1w2yr1dLfnlzYowZDZD'
    
    #ID de Pagina, posiblemente se relacione con un textbox en interfaz para ingresarlo
    pageid = '433695893782683'

    #formato de URL para la solicitud a FB
    url = 'https://graph.facebook.com/v3.1/'+pageid+'?fields=posts&access_token='+token

    try:
        #Solicitud a FB
        data_response = rqst.get(url)

        #Se genera respuesta en formato JSON
        data = data_response.json()
        posts = data['posts']

        #hacemos un ciclo para iterar a traves de las respuestas de la api
        for posts in posts['data']:

            #Extraemos de la X respuesta su ID, y la fecha, luego formateamos la fecha para poder insertarla en BD.

            id = posts['id']
            tempdate = posts['created_time']
            date = datetime.datetime.strptime(tempdate[:-5], '%Y-%m-%dT%H:%M:%S')

            cur = mysql.connection.cursor()
            result = cur.execute("SELECT * FROM tbl_posts WHERE postid = %s", [id])
            mysql.connection.commit()
            cur.close()

            try:
                if result < 1:

                    
                    if any(key in posts for key in ['message']):
                        post = posts['message']

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_posts(postid, postdate, posttext) VALUES(%s, %s, %s)", (id, date, post))
                        mysql.connection.commit()
                        cur.close()

                        print('Nuevo Insert: ' +id)

                    elif any(key in posts for key in ['story']):
                        post = posts['story']
                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_posts(postid, postdate, posttext) VALUES(%s, %s, %s)", (id, date, post))
                        mysql.connection.commit()
                        cur.close()

                        print('Nuevo Insert: ' +id)
                    
                else:
                    print('Ya existe: '+id)
            except ValueError:
                    print('This is an error: ', ValueError)
                

        return render_template('/posts.html')
    except ValueError:
        print('This is an error', ValueError)
        return render_template('/posts.html')


#EXTRAER COMENTARIOS DE POST
@app.route('/comments')
def comment():

    cur = mysql.connection.cursor()
    cur.execute("SELECT postid FROM tbl_posts ORDER BY postdate DESC")
    result = cur.fetchmany(size=15)
    cur.close()

    for x in result:
        postid = x['postid']
        

        token = 'EAAIPgJKNjsgBAMMYFgAiY1wHJyIWzP1PK0cvmkGZBfN72McbiOEX8zOjbdlpYXwDKO3FwPZC1Amofl66zGcZCeRbaknaUPNQHQN6ZBPKpcnZCGWkH8SPHv16oudct6qB11sXQxuQFZBqt7oxE6NBeWZCzDpuxq8xrV6HeqEZAfyLjTinL2UnejXJVNkbvpxz8LJ2DC6zwcWItpZBoJjdycCvVEvZBLOUf1w2yr1dLfnlzYowZDZD'

        url = 'https://graph.facebook.com/v3.1/'+postid+'?fields=comments&access_token='+token

        data_response = rqst.get(url)

        data = data_response.json()

        if any(key in data for key in ['comments']):
            comments = data['comments']

            for comments in comments['data']:
                commentid = comments['id']
                tempdate = comments['created_time']
                commentdate = datetime.datetime.strptime(tempdate[:-5], '%Y-%m-%dT%H:%M:%S')
                commenttext = comments['message']

                cur = mysql.connection.cursor()
                dbcheck = cur.execute("SELECT * FROM tbl_comments WHERE commentid = %s", [commentid])
                mysql.connection.commit()
                cur.close()

                try:
                    if dbcheck < 1:

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_comments(commentid, postid, commentdate, commenttext) VALUES(%s, %s, %s, %s)", (commentid, postid, commentdate, commenttext))
                        mysql.connection.commit()
                        cur.close()

                        print('Nuevo Insert: ' +commentid)

                    else:

                        print('Comentario ya existe: ' +commentid)
                except ValueError:
                    print('This is an error: ', ValueError)

        elif any(key in data for key in ['id']):
            
            print('No hay comentarios: ' +postid)

    return render_template('comments.html')

@app.route('/score')
def score():

    cur = mysql.connection.cursor()
    cur.execute("SELECT ts.commentid, flag, score, scoredate, tc.commenttext FROM app.tbl_sentiment AS ts INNER JOIN app.tbl_comments AS tc ON ts.commentid = tc.commentid WHERE flag = '0'")
    result = cur.fetchall()
    cur.close()

    for x in result:
        commentid = x['commentid']
        score = x['score']
        commenttext = x['commenttext']

        project_id = 'complete-will-122319'
        compute_region = 'us-central1'
        model_id = 'TCN8431143772987397459'

        automl_client = automl.AutoMlClient()
        prediction_client = automl.PredictionServiceClient()
        model_full_id = automl_client.model_path(project_id, compute_region, model_id)

        payload = {"text_snippet": {"content": str(commenttext), "mime_type": "text/txt"}}
        response = prediction_client.predict(model_full_id, payload)

        for x in response.payload:
            cat = x.display_name
            score = x.classification.score

            cur = mysql.connection.cursor()
            dbcheck = cur.execute("SELECT * FROM tbl_score_dump WHERE commentid = %s", [commentid])
            mysql.connection.commit()
            cur.execute("SELECT * FROM tbl_score_dump WHERE commentid = %s", [commentid])
            consult = cur.fetchall()
            cur.close()

            print(commentid, cat, score)


            if dbcheck < 1:

                try:
                
                    if cat == 'positivo':
                        scoreflag = '0'

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_score_dump(commentid, posscore, scoreflag) VALUES(%s, %s, %s)", ([commentid], [score], [scoreflag]))
                        mysql.connection.commit()
                        cur.close()

                    elif cat == 'negativo':
                        scoreflag = '1'

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_score_dump(commentid, negscore, scoreflag) VALUES(%s, %s, %s)", ([commentid], [score], [scoreflag]))
                        mysql.connection.commit()
                        cur.close()
                except ValueError:
                    print('This is an error: ', ValueError)
            
            else:
                for x in consult:
                    posscore = x['posscore']
                    negscore = x['negscore']

                    if posscore is None:
                        cur = mysql.connection.cursor()
                        cur.execute("UPDATE tbl_score_dump SET posscore = %s WHERE commentid = %s", ([score], [commentid]))
                        mysql.connection.commit()
                        cur.close()

                    elif negscore is None:
                        cur = mysql.connection.cursor()
                        cur.execute("UPDATE tbl_score_dump SET negscore = %s WHERE commentid = %s", ([score], [commentid]))
                        mysql.connection.commit()
                        cur.close()
            
            #print(commentid, consult)
    
    return render_template('score.html')

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
