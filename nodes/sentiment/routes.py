from flask import Blueprint, render_template, redirect, url_for
from flask_mysqldb import MySQL
from nodes.extensions import mysql
from google.cloud import automl_v1beta1 as automl

mod = Blueprint('sentiment', __name__)

@mod.route('/sentiment')
def sentiment():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM app.tbl_comments WHERE commentflag = '0'")
    result = cur.fetchall()
    cur.close()
    a=[] #CommentID List
    b=[] #Score List 1
    c=[] #Order List
    d=[] #Score List 2
    for x in result:
        commentid = x['commentid']
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
                b.append(score)
                c.append(cat)
        a.append(commentid)

    i = 0
    j = 0
    k = 0

    while i <  len(a):
        if c[j] == "positivo":
            x = b[j]
            y = b[j+1]
            new_score = x - y
            j+=2
            d.append(new_score)
        else:
            x = b[j]
            y = b[j+1]
            new_score = y - x
            j+=2
            d.append(new_score)
        i+=1

    while k < len(a):
        commentflag=1
        cur = mysql.connection.cursor()
        cur.execute('UPDATE tbl_comments SET sentimentscore = %s, commentflag = %s WHERE commentid = %s', (d[k],commentflag,a[k]))
        mysql.connection.commit()
        cur.close()
        k+=1
    
    return redirect(url_for('dashboard.dashboard'))