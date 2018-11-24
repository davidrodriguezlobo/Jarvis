from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import datetime
import json
import datetime, calendar
import requests as rqst
from google.cloud import automl_v1beta1 as automl
import sys
from os import path
import numpy as np
from PIL import Image
from wordcloud import WordCloud, STOPWORDS

app = Flask(__name__, static_url_path='/static')

#MySQL Config

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
#app.config['MYSQL_PASSWORD'] = '1234'
#app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'app'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#Initiate MySQL

mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
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
                return redirect(url_for('update'))
            else:
                flash('Invalid Login')
                return render_template('login.html')
        
        else:
            flash('Username not Found')
            return render_template('login.html')
        #Close COnnection
        cur.close()
    return render_template('login.html')

@app.route('/comments')
def comments():
    return render_template('table.html')

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


#Actualiza toda la información, incluidos Posts, Comments y Sentiment.
@app.route('/update')
def update():
    pcontador = 0
    pcontador1 = 0
    pcontadortotal = 0
    #Token Temporal
    token = 'EAAIPgJKNjsgBAEZCGQLXDXbXQ7l4ZC4UxnWYKyDNPR3nuR6Ob8ORQoBhGKw4Kmhv7ZBIlXcCgIoUjjsdkCLQz8p1NY0LrmQSSTL7jXsEWnM3lOoZBCujCiyFor7smS1plLBKCLmQ8ZA0zDuP8agnM4MuMStxZATzYZD'
    
    #ID de Pagina, posiblemente se relacione con un textbox en interfaz para ingresarlo
    pageid = '433695893782683'

    #formato de URL para la solicitud a FB 
    url = 'https://graph.facebook.com/v3.1/'+pageid+'?fields=posts&access_token='+token
    url1 = 'https://graph.facebook.com/v3.1/'+pageid+'?fields=fan_count,talking_about_count&access_token='+token

    try:

        followersraw = rqst.get(url1)
        followersdata = followersraw.json()
        fan_count = followersdata['fan_count']
        talking_about_count = followersdata['talking_about_count']

        cur = mysql.connection.cursor()
        cur.execute('UPDATE tbl_businessdata SET fan_count = %s, talking_about_count = %s WHERE month = month(now()) AND year = year(now())', (fan_count,talking_about_count))
        mysql.connection.commit()
        cur.close() 
        

    except ValueError:
       print('This is an error', ValueError)

    try:
        #Solicitud a FB
        p_data_response = rqst.get(url)

        #Se genera respuesta en formato JSON
        p_data = p_data_response.json()
        p_posts = p_data['posts']

        #hacemos un ciclo para iterar a traves de las respuestas de la api
        for p_posts in p_posts['data']:

            #Extraemos de la X respuesta su ID, y la fecha, luego formateamos la fecha para poder insertarla en BD.

            p_id = p_posts['id']
            tempdate = p_posts['created_time']
            p_date = datetime.datetime.strptime(tempdate[:-5], '%Y-%m-%dT%H:%M:%S')

            cur = mysql.connection.cursor()
            p_result = cur.execute("SELECT * FROM tbl_posts WHERE postid = %s", [p_id])
            mysql.connection.commit()
            cur.close()

            try:
                if p_result < 1:
                    
                    if any(key in p_posts for key in ['message']):
                        post = p_posts['message']

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_posts(postid, postdate, posttext) VALUES(%s, %s, %s)", (p_id, p_date, post))
                        mysql.connection.commit()
                        cur.close()
                        pcontador += 1
                        #print('Nuevo Insert: ' +p_id)

                    elif any(key in p_posts for key in ['story']):
                        post = p_posts['story']
                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_posts(postid, postdate, posttext) VALUES(%s, %s, %s)", (p_id, p_date, post))
                        mysql.connection.commit()
                        cur.close()
                        pcontador1 += 1
                        #print('Nuevo Insert: ' +p_id)
                    pcontadortotal = pcontador + pcontador1
                else:
                    pass
                    #print('Ya existe: '+p_id)
            except ValueError:
                    print('This is an error: ', ValueError)
                
    except ValueError:
        print('This is an error', ValueError)

    ccontadortotal = 0
    cur = mysql.connection.cursor()
    cur.execute("SELECT postid FROM tbl_posts ORDER BY postdate DESC")
    c_result = cur.fetchmany(size=25)
    cur.close()

    for c_x in c_result:
        c_postid = c_x['postid']

        token = 'EAAIPgJKNjsgBAEZCGQLXDXbXQ7l4ZC4UxnWYKyDNPR3nuR6Ob8ORQoBhGKw4Kmhv7ZBIlXcCgIoUjjsdkCLQz8p1NY0LrmQSSTL7jXsEWnM3lOoZBCujCiyFor7smS1plLBKCLmQ8ZA0zDuP8agnM4MuMStxZATzYZD'

        url = 'https://graph.facebook.com/v3.1/'+c_postid+'?fields=comments&access_token='+token

        c_data_response = rqst.get(url)

        c_data = c_data_response.json()

        if any(key in c_data for key in ['comments']):
            c_comments = c_data['comments']

            for c_comments in c_comments['data']:
                c_commentid = c_comments['id']
                c_tempdate = c_comments['created_time']
                c_commentdate = datetime.datetime.strptime(c_tempdate[:-5], '%Y-%m-%dT%H:%M:%S')
                c_commenttext = c_comments['message']

                cur = mysql.connection.cursor()
                c_dbcheck = cur.execute("SELECT * FROM tbl_comments WHERE commentid = %s", [c_commentid])
                mysql.connection.commit()
                cur.close()

                try:
                    if c_dbcheck < 1:

                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_comments(commentid, postid, commentdate, commenttext) VALUES(%s, %s, %s, %s)", (c_commentid, c_postid, c_commentdate, c_commenttext))
                        mysql.connection.commit()
                        cur.close()
                        ccontadortotal += 1
                        #print('Nuevo Insert: ' +c_commentid)

                    else:
                        pass
                        #print('Comentario ya existe: ' +c_commentid)
                except ValueError:
                    print('This is an error: ', ValueError)

        elif any(key in c_data for key in ['id']):
            pass
            #print('No hay comentarios: ' +c_postid)

    contador1 = 0
    contador2 = 0
    scontadortotal = 0
    cur = mysql.connection.cursor()
    cur.execute("SELECT ts.commentid, flag, score, scoredate, tc.commenttext FROM app.tbl_sentiment AS ts INNER JOIN app.tbl_comments AS tc ON ts.commentid = tc.commentid WHERE flag = '0'")
    result = cur.fetchall()
    cur.close()

    for x in result:
        commentid = x['commentid']
        score = x['score']
        commenttext = x['commenttext']

        if commenttext == '':
            pass
        else:
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

                #print(commentid, cat, score)

                if dbcheck < 1:

                    try:
                    
                        if cat == 'positivo':
                            scoreflag = '0'

                            cur = mysql.connection.cursor()
                            cur.execute("INSERT INTO tbl_score_dump(commentid, posscore, scoreflag) VALUES(%s, %s, %s)", ([commentid], [score], [scoreflag]))
                            mysql.connection.commit()
                            cur.close()
                            contador1 += 1

                        elif cat == 'negativo':
                            scoreflag = '1'

                            cur = mysql.connection.cursor()
                            cur.execute("INSERT INTO tbl_score_dump(commentid, negscore, scoreflag) VALUES(%s, %s, %s)", ([commentid], [score], [scoreflag]))
                            mysql.connection.commit()
                            cur.close()
                            contador2 += 1
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
    scontadortotal = contador1 + contador2
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard(chartID = 'chart_ID', chart_type = 'line', chart_height = 500):
    
    cur = mysql.connection.cursor()
    cur.execute("select max(day(commentdate))  from  app.tbl_comments where month(commentdate) = month( curdate())")
    prueba2 = cur.fetchall()
    cur.close()

    #daily comment count
    for y in prueba2:
        maxday = y['max(day(commentdate))']
        myLabels = []
        myValues = []
        n = maxday + 1
        for i in range(1, n):
            myLabels.append(i) #Agrega día 1 hasta maxday al array

        for j in myLabels:
            cur = mysql.connection.cursor()
            cur.execute("SELECT count(*) FROM app.tbl_comments where month(commentdate) = month( curdate()) AND day(commentdate) = %s", ([j]))
            prueba = cur.fetchall()
            cur.close()
            
            for k in prueba:
                value = (k['count(*)'])
                myValues.append(value)
  
        #Graph Values
        labels = myLabels
        values = myValues

    #Pie Values

    cur = mysql.connection.cursor()
    cur.execute("SELECT score FROM app.tbl_sentiment INNER JOIN app.tbl_comments ON app.tbl_sentiment.commentid = app.tbl_comments.commentid WHERE month(commentdate) = month(now()) AND month(commentdate) = month(now());")
    result = cur.fetchall()
    cur.close()

    pscore = 0
    nscore = 0

    for sentiment in result:
        score = sentiment['score']
        if score > 0:
            pscore += 1
        else:
            nscore += 1


    labels1 = ["Positivo","Negativo"]
    values1 = [pscore,nscore]
    colors1 = ["#6EA4BF","#41337A"]

    #Monthly sentiment count
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    #day = now.day

    cur = mysql.connection.cursor()
    #cur.execute('SELECT * FROM app.tbl_monthsent WHERE month = %s AND year = %s', ([month],[year]))
    cur.execute('SELECT * FROM app.tbl_monthsent')
    monthly_sentiment = cur.fetchall()
    cur.close()
    avg_sent = []
    for sentiment in monthly_sentiment:
        m_sentiment = sentiment[('avgsentiment')]
        avg_sent.append(m_sentiment)

    arr = []
    if month == 1:
        arr = ["Enero"]
    elif month == 2:
        arr = ["Enero", "Febrero"]
    elif month == 3:
        arr = ["Enero", "Febrero", "Marzo"]
    elif month == 4:
        arr = ["Enero", "Febrero", "Marzo", "Abril"]
    elif month == 5:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo"]
    elif month == 6:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
    elif month == 7:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio"]
    elif month == 8:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto"]
    elif month == 9:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre"]
    elif month == 10:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]
    elif month == 11:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre"]
    elif month == 12:
        arr = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT avgsentiment FROM app.tbl_monthsent WHERE month = %s AND year = %s', ([month],[year]))
    mtdsent = cur.fetchall()
    cur.close()

    for mtd in mtdsent:
        r = lambda f,p: f - f % p
        mtdsentiment = mtd[('avgsentiment')]
        mtdsentiment = mtdsentiment * 100
        mtdsentiment = "%.2f" % mtdsentiment
        
    labels3 = arr
    values3 = list(reversed(avg_sent))

    cur = mysql.connection.cursor()
    cur.execute('SELECT fan_count FROM app.tbl_businessdata WHERE month = %s AND year = %s', ([month],[year]))
    follower_count = cur.fetchall()
    cur.close()
    
    for x in follower_count:
        fan_count = x[('fan_count')]

        if fan_count > 999:
            fan_count = fan_count / 1000
            tag = 'K'
        elif fan_count > 999999:
            fan_count = fan_count / 1000000
            tag = 'M'
        else:
            tag = ''
    

    cur = mysql.connection.cursor()
    cur.execute("SELECT text FROM app.tbl_wordcloud WHERE year = year(now()) AND month = month(now()) AND polarity = 'positivo'")
    poswordcloud = cur.fetchall()
    cur.close()

    cur = mysql.connection.cursor()
    cur.execute("SELECT text FROM app.tbl_wordcloud WHERE year = year(now()) AND month = month(now()) AND polarity = 'negativo'")
    negwordcloud = cur.fetchall()
    cur.close()

    for ptext in poswordcloud:
        poswords = ptext[('text')]
    for ntext in negwordcloud:
        negwords = ntext[('text')]

    
    # create numpy araay for wordcloud mask image
    mask = np.array(Image.open(r"C:\Users\David\Desktop\Jarvis\static\cloud.png"))

        # create set of stopwords	
    stopwords = set(STOPWORDS)
    new_words = ['un', 'una', 'unas', 'unos', 'uno', 'sobre', 'todo', 'también', 'tras', 'otro', 'algún', 'alguno', 'alguna', 'algunos', 'algunas', 'ser', 'es', 'soy', 'eres', 'somos', 'sois', 'estoy', 'esta', 'estamos', 'estais', 'estan', 'como', 'en', 'para', 'atras', 'porque', 'por qué', 'estado', 'estaba', 'ante', 'antes', 'siendo', 'ambos', 'pero', 'por', 'poder', 'puede', 'puedo', 'podemos', 'podeis', 'pueden', 'fui', 'fue', 'fuimos', 'fueron', 'hacer', 'hago', 'hace', 'hacemos', 'haceis', 'hacen', 'cada', 'fin', 'incluso', 'primero', 'desde', 'conseguir', 'consigo', 'consigue', 'consigues', 'conseguimos', 'consiguen', 'ir', 'voy', 'va', 'vamos', 'vais', 'van', 'vaya', 'gueno', 'ha', 'tener', 'tengo', 'tiene', 'tenemos', 'teneis', 'tienen', 'el', 'la', 'lo', 'las', 'los', 'su', 'aqui', 'mio', 'tuyo', 'ellos', 'ellas', 'nos', 'nosotros', 'vosotros', 'vosotras', 'si', 'dentro', 'solo', 'solamente', 'saber', 'sabes', 'sabe', 'sabemos', 'sabeis', 'saben', 'ultimo', 'largo', 'bastante', 'haces', 'muchos', 'aquellos', 'aquellas', 'sus', 'entonces', 'tiempo', 'verdad', 'verdadero', 'verdadera', 'cierto', 'ciertos', 'cierta', 'ciertas', 'intentar', 'intento', 'intenta', 'intentas', 'intentamos', 'intentais', 'intentan', 'dos', 'bajo', 'arriba', 'encima', 'usar', 'uso', 'usas', 'usa', 'usamos', 'usais', 'usan', 'emplear', 'empleo', 'empleas', 'emplean', 'ampleamos', 'empleais', 'valor', 'muy', 'era', 'eras', 'eramos', 'eran', 'modo', 'bien', 'cual', 'cuando', 'donde', 'mientras', 'quien', 'con', 'entre', 'sin', 'podria', 'podrias', 'podriamos', 'podrian', 'podriais', 'yo', 'aquel', 'yo', 'aquel', 'mis', 'tu', 'que']
    stopwords.update(new_words)

    print(stopwords)

        # create wordcloud object
    wc = WordCloud(background_color="white", max_words=200, mask=mask, stopwords=stopwords)
    wc1 = WordCloud(background_color="white", max_words=200, mask=mask, stopwords=stopwords)
        
        # generate wordcloud
    wc.generate(poswords)
    wc1.generate(negwords)

        # save wordcloud
    wc.to_file(r"C:\Users\David\Desktop\Jarvis\static\wc.png")
    wc1.to_file(r"C:\Users\David\Desktop\Jarvis\static\wc1.png")

    
    return render_template('dashboard.html', values=values, labels=labels, set=zip(values1, labels1, colors1), values3=values3, labels3=labels3, mtdsentiment=mtdsentiment, fan_count=fan_count, tag=tag)

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
