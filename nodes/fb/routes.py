from flask import Blueprint, request, redirect, url_for
from flask_mysqldb import MySQL
from nodes.extensions import mysql
import requests as rqst
import datetime, calendar

mod = Blueprint('fb', __name__)

@mod.route('/fb')
def fb():  

    #Token Temporal
    token = 'EAAIPgJKNjsgBAJHXGg2CGBJjexj7kKI1cfjAud0VVpKqCDOR9T39vZBhIRt51zM9pYLj3V1VgR1imTW2HQecKYAcrJZBG6slFqE336L7VjklWZADt1XJYHMywwEqOzjmU4ZAMZCXobLe0UQNGdUpZC2FBVgDQWZACGOeBXoRZBUZASgZDZD'
    
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
                        #print('Nuevo Insert: ' +p_id)

                    elif any(key in p_posts for key in ['story']):
                        post = p_posts['story']
                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO tbl_posts(postid, postdate, posttext) VALUES(%s, %s, %s)", (p_id, p_date, post))
                        mysql.connection.commit()
                        cur.close()
                        #print('Nuevo Insert: ' +p_id)
                else:
                    pass
                    #print('Ya existe: '+p_id)
            except ValueError:
                    print('This is an error: ', ValueError)
                
    except ValueError:
        print('This is an error', ValueError)

    cur = mysql.connection.cursor()
    cur.execute("SELECT postid FROM tbl_posts ORDER BY postdate DESC")
    c_result = cur.fetchmany(size=25)
    cur.close()

    for c_x in c_result:
        c_postid = c_x['postid']

        token = 'EAAIPgJKNjsgBAJHXGg2CGBJjexj7kKI1cfjAud0VVpKqCDOR9T39vZBhIRt51zM9pYLj3V1VgR1imTW2HQecKYAcrJZBG6slFqE336L7VjklWZADt1XJYHMywwEqOzjmU4ZAMZCXobLe0UQNGdUpZC2FBVgDQWZACGOeBXoRZBUZASgZDZD'

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

                        #print('Nuevo Insert: ' +c_commentid)

                    else:
                        pass
                        #print('Comentario ya existe: ' +c_commentid)
                except ValueError:
                    print('This is an error: ', ValueError)

        elif any(key in c_data for key in ['id']):
            pass
            #print('No hay comentarios: ' +c_postid)
    return redirect(url_for('sentiment.sentiment'))