drop table if exists playlist;
create table playlist (
  playlist_id integer primary key autoincrement,
  label text not null,
  comment text
);

drop table if exists song;
create table song (
  song_id integer primary key autoincrement,
  in_playlist integer not null,
  netease_id integer not null,
  song_name text not null,
  artist_name text not null,
  album_name text not null,
  mp3_url text not null
);
