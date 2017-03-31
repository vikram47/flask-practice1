import os
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from cassandra.cluster import Cluster
import cassandra
import uuid

app = Flask(__name__)  # create the application instance

app.config.from_object(__name__)  # load config from this file , flaskr.py

app.config.update(dict(
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='secret'
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)


# Routes
@app.route('/')
def show_entries():
    db = get_db()
    notes = db.execute('SELECT title, text FROM notes')
    return render_template('show_entries.html', notes=notes)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('INSERT INTO notes (id, title, text) VALUES (%s, %s, %s)', [uuid.uuid1(),
                                                                           request.form['title'], request.form['text']])
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


# DB related functions
def connect_db():
    """Connects to the specific database."""
    print('Inside connect_db.')
    cluster = Cluster()
    session = cluster.connect('flaskr')
    return session


def init_db():
    try:
        cluster = Cluster()
        session = cluster.connect()
        print('Creating Keyspace flaskr..')
        cql_command = """CREATE KEYSPACE flaskr WITH
        REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 3 };"""
        session.execute(cql_command)
        try:
            session.execute(cql_command)
            print('Keyspace flaskr created.')
        except cassandra.AlreadyExists as e:
            print("Keyspace already exists")
            pass

        try:
            session.set_keyspace('flaskr')
            print('Creating table notes..')
            cql_command = """CREATE TABLE notes (id uuid PRIMARY KEY,title varchar,text varchar);"""
            session.execute(cql_command)
            print('Table notes created.')
        except cassandra.AlreadyExists as e:
            print("Table already exists")

    except Exception as e:
        print('Could not connect to DB', e)


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    print('Inside get_db.')
    if not hasattr(g, 'cassandra_db'):
        g.cassandra_db = connect_db()
    return g.cassandra_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    print('Inside close_db.')
    if hasattr(g, 'cassandra_db'):
        g.cassandra_db.cluster.shutdown()


if __name__ == '__main__':
    app.run()
