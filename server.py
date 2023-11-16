
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, jsonify,request, render_template, g, redirect, Response, abort, url_for, flash, session
import uuid
from datetime import datetime
#from sentence_transformers import SentenceTransformer, util


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.debug = True
app.secret_key = 'your_secret_key'

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.75.94.195/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.75.94.195/proj1part2"
#
DATABASEURI = "postgresql://yz4326:442835@34.74.171.121/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
conn = engine.connect()

# The string needs to be wrapped around text()

#conn.execute(text("""CREATE TABLE IF NOT EXISTS test (
 # id serial,
  #name text
#);"""))
#conn.execute(text("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');"""))

# To make the queries run, we need to add this commit line

#conn.commit() 

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
    if 'personID' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html')

@app.route('/dashboard')
def dashboard():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data

  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)
  cursor = g.conn.execute(text("SELECT job_id, job_title, url, required_skills, preferred_skills, min_salary, max_salary, duration FROM Job_Post"))
  g.conn.commit()
  jobItems = cursor.mappings().all()
  cursor.close()
  # 查询当前用户已应聘的职位
  cursor = g.conn.execute(text("SELECT job_id FROM Apply WHERE person_id = :person_id"), {'person_id': session.get('personID')})
  applied_jobsmap = cursor.mappings().all()
  applied_jobs = [row['job_id'] for row in applied_jobsmap]
  cursor.close()
  # 将查询结果传递给前端
  context = dict(
      data=jobItems[:10],
      applied_jobs=applied_jobs
  )
  return render_template("dashboard.html", **context)

@app.route('/apply-job', methods=['POST'])
def apply_job():
    if 'personID' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    data = request.get_json()
    job_id = data.get('job_id')
    person_id = session['personID']
    application_id = str(uuid.uuid4()).replace('-', '')[:20]  # 生成唯一的 application ID
    current_date = datetime.now().date()

    # 插入新的应聘记录到 APPLY 表
    try:
        g.conn.execute(text("""
            INSERT INTO APPLY (application_id, job_id, person_id, start_date, status, last_update_date)
            VALUES (:application_id, :job_id, :person_id, :start_date, 'Pending', :last_update_date)
        """), {
            'application_id': application_id,
            'job_id': job_id,
            'person_id': person_id,
            'start_date': current_date,
            'last_update_date': current_date
        })
        g.conn.commit()
        return jsonify({'applied': True})
    except Exception as e:
        g.conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/jobinfo/<job_id>')
def jobinfo(job_id):
    return render_template('jobinfo.html')
   
@app.route('/track')
def track():
  sql_query = text("""
    SELECT j.job_id, j.job_title, a.start_date, a.status, a.last_update_date, a.application_id 
    FROM Job_Post j, Apply a 
    WHERE a.person_id = :person_id 
    AND j.job_id = a.job_id
""")
  
  cursor = g.conn.execute(sql_query,{'person_id':session.get('personID')})
  g.conn.commit()
  applyRecord = cursor.mappings().all()
  cursor.close()
  context = dict(data = applyRecord)
  return render_template("track.html",**context)

@app.route('/editApplyRecord/<application_id>')
def editApplyRecord(application_id):
    cursor = g.conn.execute(text("SELECT * FROM Apply WHERE application_id = :application_id"), {'application_id': application_id})
    application = cursor.fetchone()
    cursor.close()
    if application is not None:
      application = dict(data = application)
    if application is None:
        return "Application record not found", 404

    return render_template('editApplyRecord.html', **application)

@app.route('/saveApplyRecord/<application_id>', methods=['POST'])
def saveApplyRecord(application_id):
    status = request.form['status']
    start_date = request.form['start_date']
    last_update_date = request.form['last_update_date']
    try:
        g.conn.execute(text("""
            UPDATE Apply SET status = :status, start_date = :start_date, last_update_date = :last_update_date WHERE application_id = :application_id
        """), {'status': status, 'start_date': start_date, 'last_update_date': last_update_date, 'application_id': application_id})
        g.conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        g.conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/deleteApplyRecord/<application_id>', methods=['POST'])
def deleteApplyRecord(application_id):
    try:
        g.conn.execute(text("DELETE FROM Apply WHERE application_id = :application_id"), {'application_id': application_id})
        g.conn.commit()
        return '', 204  # 返回 204 No Content 表示成功删除
    except Exception as e:
        print(e)  # 在生产环境中，应该使用更合适的错误处理
        return jsonify({'error': str(e)}), 500

@app.route('/addApplyRecord/<application_id>')
def addApplyRecord(application_id):
   return render_template('addApplyRecord.html')

@app.route('/recommendations')
def recommendations():
  print("-----")
  print(session.get('personID'))
  sql_query = text("""
    SELECT j.job_id, j.job_title, j.required_skills, j.preferred_skills
    FROM Job_Post j, Apply a 
    WHERE a.person_id = :person_id 
    AND j.job_id = a.job_id
""")
  cursor = g.conn.execute(sql_query,{'person_id':session.get('personID')})
  g.conn.commit()
  results_list = cursor.fetchall()
  cursor.close()
  print(results_list)
  extracted_values = [[value for value in tup[1:] if value is not None] for tup in results_list]
  job_list = [tup[0] for tup in results_list]
  # Join the inner lists into strings and then join these strings into one large string
  target_string = ' '.join([' '.join(sublist) for sublist in extracted_values])
  print(job_list)
  print(target_string)
  if job_list:
    job_tuple = tuple(job_list)
  else:
    # Handle the case where job_list is empty
    job_tuple = ('dummy_value',)
  model = SentenceTransformer('all-MiniLM-L6-v2')
  sql_query = text("""
    SELECT *
    FROM Job_Post j
    where j.job_id not in :jobtuple
""")
  cursor = g.conn.execute(sql_query,{'jobtuple':job_tuple})
  jobMap = cursor.mappings().all()
  g.conn.commit()
  cursor.close()
  combined_strings = []
  for job in jobMap:
    combined = job['job_title']
    if job['required_skills']:
        combined += " " + job['required_skills']
    if job['preferred_skills']:
        combined += " " + job['preferred_skills']
    combined_strings.append(combined)
    # Generate embeddings
  #target_embedding = model.encode(target_string, convert_to_tensor=True)
  #job_embeddings = model.encode(combined_strings, convert_to_tensor=True)

  # Calculate cosine similarities
  #cosine_scores = util.pytorch_cos_sim(target_embedding, job_embeddings)

  # Find the top 5 most similar jobs
  #top_5_indices = cosine_scores.argsort(descending=True)[0][:5]

  #top_5_jobs = [jobMap[i] for i in top_5_indices]
  #context = dict(
     #data = top_5_jobs,
     #applied_jobs = []
     #)

  return render_template("recommendations.html")

@app.route('/aboutus')
def aboutus():
  return render_template("aboutus.html")
@app.route('/myprofile')
def myprofile():
  sql_query = text('SELECT email,phone,address,websites,resume_url from Applicants where person_id = :person_id')
  cursor = g.conn.execute(sql_query,{'person_id':session.get('personID')})
  g.conn.commit()
  profile = cursor.fetchone()
  cursor.close()
  context = dict(data = profile)
  return render_template("myprofile.html", **context)

@app.route('/saveProfile', methods=['POST'])
def saveProfile():
  try:
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    websites = request.form['websites']
    resume_url = request.form['resume_url']
    print(email, phone, address, websites, resume_url, session.get('personID'))
    if not email:
      return jsonify({'message': 'Email is required.'}), 400
    g.conn.execute(text("""
        UPDATE Applicants SET email = :email, phone = :phone, address = :address, websites = :websites, resume_url = :resume_url WHERE person_id = :person_id
    """), {'email': email, 'phone': phone, 'address': address, 'websites': websites, 'resume_url': resume_url,'person_id': session.get('personID')})
    g.conn.commit()
    return jsonify({'message': 'Profile updated successfully.'}), 200
  except Exception as e:
    g.conn.rollback()
    print(str(e))
    return jsonify({'error': str(e)}), 500

# Example of adding new data to the database
#@app.route('/add', methods=['POST'])
#def add(): 
  #name = request.form['name']
  #params_dict = {"name":name}
  #g.conn.execute(text('INSERT INTO test(name) VALUES (:name)'), params_dict)
  #g.conn.commit()
  #return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userEmail = request.form['userEmail']
        cursor = g.conn.execute(text("SELECT DISTINCT * FROM Applicants where email=:user_email"),{'user_email':userEmail})
        g.conn.commit()
        applicantsInfo = cursor.mappings().all()
        cursor.close()
        person_id = [person['person_id'] for person in applicantsInfo]
        print(person_id)
        if len(person_id)!=0:
            session['personID'] = person_id[0]
            return redirect(url_for('index'))
        flash('Invalid userEmail')
    return render_template('login.html')
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        userEmail = request.form['userEmail']
        cursor = g.conn.execute(text("SELECT email FROM Applicants"))
        g.conn.commit()
        emails = cursor.mappings().all()
        email_list = [email['email'] for email in emails]
        print(emails)
        cursor.close()
        if userEmail in email_list:
            flash('User Email already exists.')
            return redirect(url_for('login'))
        person_id = str(uuid.uuid4()).replace('-', '')[:20]
        params_dict = {"person_id":person_id,"email":userEmail}
        cursor1 = g.conn.execute(text('INSERT INTO Applicants(person_id,email) VALUES (:person_id,:email)'), params_dict)
        g.conn.commit()
        cursor1.close()
        flash('Successfully sign up, please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('personID', None)  # 移除 session 中的用户名，实现用户登出
    return redirect(url_for('index'))

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
