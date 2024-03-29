# qlive-couchbase
quake live zmq stats to couchbase database via python

## Quickstart on CentOS 7
  ```
  sudo su root
  wget http://packages.couchbase.com/releases/couchbase-release/couchbase-release-1.0-4-x86_64.rpm
  rpm -iv couchbase-release-1.0-4-x86_64.rpm
  yum install libcouchbase-devel gcc gcc-c++ python-devel python-pip
  pip install couchbase
  pip install zmqpy
  pip install unidecode
  exit
  ```
## Sample config
```
{
  "ql_server":{
    "zmq_stats_uri":"tcp://localhost:28970",
    "zmq_stats_password":"changeme",
    "zmq_socket_timeout":1000
  },
  "couchbase_server":{
    "uri":"couchbase://localhost",
    "username":"user",
    "password":"changeme",
    "buckets":[
      {
        "ql_msg_type":"PLAYER_KILL",
        "bucket_name":"qlive-player-kill"
      },
      {
        "ql_msg_type":"PLAYER_DEATH",
        "bucket_name":"qlive-player-death"
      },
      {
        "ql_msg_type":"PLAYER_STATS",
        "bucket_name":"qlive-player-stats"
      },
      {
        "ql_msg_type":"PLAYER_MEDAL",
        "bucket_name":"qlive-player-medal"
      },
      {
        "ql_msg_type":"MATCH_REPORT",
        "bucket_name":"qlive-player-death"
      },
      {
        "ql_msg_type":"ROUND_OVER",
        "bucket_name":"qlive-round-over"
      }
    ]
  }
}
```

## Run
```
python qlive-couchbase.py -d -c conf.json
```