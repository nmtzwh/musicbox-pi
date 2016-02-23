# -*- coding: utf-8 -*-
"""
    neteasepy
    ~~~~~~~~

    My NetEase Music player on Raspberry Pi written with Flask and sqlite3.
    (Rewrite from flask example: 'minitwit' )

    :copyright: (c) 2016 by Tom Zeng.
"""

# import time
from sqlite3 import dbapi2 as sqlite3
# from hashlib import md5
# from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
# from werkzeug import check_password_hash, generate_password_hash
import player
import api


# configuration
DATABASE = './neteasepy.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

class MyFlask(Flask):
    def __init__(self, * args, ** kwargs):
        super(MyFlask, self).__init__(*args, **kwargs)
        self.player = player.Player()
        self.search_result = []

# create our little application :)
app = MyFlask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('NETEASEPY_SETTINGS', silent=True)

# create player
# player = player.Player()
netease = api.NetEase()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def get_playlist_id(label):
    """Convenience method to look up the id for a playlist."""
    rv = query_db('select playlist_id from playlist where label = ?',
                  [label], one=True)
    return rv[0] if rv else None


@app.before_request
def before_request():
    g.playlist = None
    g.search = None
    if 'playlist_id' in session:
        g.playlist = query_db('select * from playlist where playlist_id = ?',
                          [session['playlist_id']], one=True)


@app.route('/')
def all_songs():
    """Displays the latest songs of all playlists."""
    return render_template('stream.html', songs=query_db('''
        select song.*, playlist.* from song, playlist
        where song.in_playlist = playlist.playlist_id
        order by song.song_id desc limit ?''', [PER_PAGE]))


@app.route('/playlist/<playlist_id>')
def playlist_content(playlist_id):
    """Shows songs in a playlist."""
    profile_playlist = query_db('select * from playlist where playlist_id = ?',
                            [playlist_id], one=True)
    if profile_playlist is None:
        abort(404)
    return render_template('stream.html', songs=query_db('''
        select song.*, playlist.* from song, playlist
        where song.in_playlist = playlist.playlist_id and (
            song.in_playlist = ? )
        order by song.song_id desc limit ?''',
        [profile_playlist['playlist_id'], PER_PAGE]), playlist=profile_playlist)


@app.route('/add_song/<int:songindex>')
def add_song(songindex=0):
    """Registers a new song for the playlist."""
    if 'playlist_id' not in session:
        abort(401)
    if songindex != 0 and len(app.search_result)>0:
        songindex = songindex - 1
        db = get_db()
        db.execute('''insert into song (in_playlist, netease_id, song_name, artist_name, album_name, mp3_url)
                   values (?, ?, ?, ?, ?, ?)''', (session['playlist_id'], app.search_result[songindex]['netease_id'], app.search_result[songindex]['song_name'], 
                                                  app.search_result[songindex]['artist_name'], app.search_result[songindex]['album_name'], app.search_result[songindex]['mp3_url']))
        db.commit()
        flash('Your song was added')
    else:
        flash('No song was added')
    return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))

@app.route('/remove/<int:song_id>')
def remove_song(song_id):
    """Delete an old song from database."""
    db = get_db()
    db.execute('''delete from song where song_id = ? ''', [song_id])
    db.commit()
    flash('That song was removed')
    return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))


@app.route('/choose', methods=['GET', 'POST'])
def choose_playlist():
    """Choose the playlist."""
    # if g.playlist:
    #     return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))
    error = None
    if request.method == 'POST':
        playlist = query_db('''select * from playlist where
            playlist_id = ?''', [request.form['playlist_id']], one=True)
        if playlist is None:
            error = 'Invalid playlist id'
        else:
            flash('You have chosen a playlist.')
            session['playlist_id'] = playlist['playlist_id']
            return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))
    return render_template('playlist.html', error=error, playlist=query_db('''
                            select * from playlist order by playlist_id desc'''))

@app.route('/remove_playlist/<int:playlist_id>')
def remove_playlist(playlist_id):
    """Delete an old playlist and all the songs in it from database."""
    db = get_db()
    db.execute('''delete from song where in_playlist = ? ''', [playlist_id])
    db.execute('''delete from playlist where playlist_id = ? ''', [playlist_id])
    db.commit()
    flash('That playlist was removed')
    return redirect(url_for('choose_playlist'))

@app.route('/add_playlist', methods=['GET', 'POST'])
def add_playlist():
    """Registers the playlist."""
    # if g.user:
    #     return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['label']:
            error = 'You have to enter a label'
        elif get_playlist_id(request.form['label']) is not None:
            error = 'The label is already used'
        else:
            db = get_db()
            db.execute('''insert into playlist (
              label, comment) values (?, ?)''',
              [request.form['label'], request.form['comment']])
            db.commit()
            flash('You were successfully registered a new playlist.')
            return redirect(url_for('choose_playlist'))
    return render_template('register.html', error=error)

@app.route('/play/<int:song_id>')
def play_songs(song_id):
    """Play all the songs from a list, begin with current song."""
    url_list = []
    current_song = query_db('''select mp3_url from song
                          where song_id = ?''',
                          [song_id], one=True)[0]
    next_urls = query_db('''select mp3_url from song
                          where in_playlist = ?
                          order by RANDOM()''',
                          [session['playlist_id']])
    url_list.append(current_song)
    for i in range(0, len(next_urls)):
        url_list.append(next_urls[i][0])
    app.player.playUrl(url_list)
    flash('Start playing ... ')
    return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))


@app.route('/stop')
def stop_playing():
    """!!! stop playing !!!"""
    if 'playlist_id' not in session:
        abort(401)
    app.player.stop()
    flash('Stop playing. ')
    return redirect(url_for('playlist_content', playlist_id=session['playlist_id']))

def getSongInfo(searchStr):
    data = netease.search(searchStr)
    song_ids = []
    if 'songs' in data['result']:
        if 'mp3Url' in data['result']['songs']:
            songs = data['result']['songs']
        # if search song result do not has mp3Url
        # send ids to get mp3Url
        else:
            for i in range(0, len(data['result']['songs'])):
                song_ids.append(data['result']['songs'][i]['id'])
            songs = netease.songs_detail(song_ids)
        songinfo =  netease.dig_info(songs, 'songs')
    else:
        songinfo = []
    return songinfo


@app.route('/search', methods=['GET','POST'])
def search():
    """search song online."""
    error = None
    songinfo = []
    app.search_result = []
    if request.method == 'POST':
        if not request.form['searchStr']:
            error = 'You have to enter some shit ...'
        else:
            songinfo = getSongInfo(request.form['searchStr'])  # add search type in the future!!!
            if len(songinfo) == 0:
                error = 'Sorry, this song cannot be found T^T'
    for i in range(0, len(songinfo)):
        temp = dict(netease_id=songinfo[i]['song_id'], song_name=songinfo[i]['song_name'], artist_name=songinfo[i]['artist'],
                    album_name=songinfo[i]['album_name'], mp3_url=songinfo[i]['mp3_url'])
        app.search_result.append(temp)            
    flash('Results are shown below: ')
    return render_template('search.html', error=error, songs=app.search_result)


# @app.route('/logout')
# def logout():
#     """Logs the user out."""
#     flash('You were logged out')
#     session.pop('user_id', None)
#     return redirect(url_for('public_timeline'))


# add some filters to jinja
# app.jinja_env.filters['datetimeformat'] = format_datetime
# app.jinja_env.filters['gravatar'] = gravatar_url

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)

