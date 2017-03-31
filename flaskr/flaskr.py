import os
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from cassandra.cluster import Cluster

app = Flask(__name__)  # create the application instance

app.config.from_object(__name__)  # load config from this file , flaskr.py

app.config.update(dict(
    USERNAME='admin',
    PASSWORD='secret'
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)


# Routes
@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute('SELECT title, text FROM entries ORDER BY id DESC')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('INSERT INTO entries (title, text) VALUES (?, ?)', [request.form['title'], request.form['text']])
    db.commit()
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
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


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
    app.run(port=6000)
