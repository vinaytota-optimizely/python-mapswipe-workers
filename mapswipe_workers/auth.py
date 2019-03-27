#!/usr/bin/python3
#
# Author: B. Herfort, M. Reinmuth, 2017
############################################

import sys
import os.path
import json

import pyrebase
import psycopg2 # handle postgres
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from mapswipe_workers.definitions import CONFIG_PATH
from mapswipe_workers.definitions import ROOT_DIR
from mapswipe_workers.definitions import SERVICE_ACCOUNT_KEY_PATH


def load_config():
    """
    Loads the user configuration values.

    Returns
    -------
    dictonary
    """
    with open(CONFIG_PATH) as f:
        CONFIG = json.load(f)
    return CONFIG


def firebaseDB():
    # Fetch the service account key JSON file contents
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    config = load_config()
    databaseURL = config['firebase']['database_url']

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': databaseURL
    })

    return db


# Configuration of the firebase database
def firebase_admin_auth():
    # TODO: Delete this function after transition of code base to firebaseDB()
    CONFIG = load_config()
    try:
        api_key = CONFIG['firebase']['api_key']
        auth_domain = CONFIG['firebase']['auth_domain']
        database_url = CONFIG['firebase']['database_url']
        storage_bucket = CONFIG['firebase']['storage_bucket']
        service_account = CONFIG['firebase']['service_account']
        # print('use configuration for psql as provided by config.json')
    except:
        # Default Configuration
        raise Exception('could not get firebase informtaion from config file')

    # adapt this to your firebase setting
    config = {
        "apiKey": api_key,
        "authDomain": auth_domain,
        "databaseURL": database_url,
        "storageBucket": storage_bucket,
        # this is important if you want to login as admin
        "serviceAccount": SERVICE_ACCOUNT_KEY_PATH
    }
    firebase = pyrebase.initialize_app(config)
    return firebase


def dev_firebase_admin_auth():
    # TODO: Delete this function after transition of code base to firebaseDB()
    CONFIG = load_config()
    try:
        api_key = CONFIG['dev_firebase']['api_key']
        auth_domain = CONFIG['dev_firebase']['auth_domain']
        database_url = CONFIG['dev_firebase']['database_url']
        storage_bucket = CONFIG['dev_firebase']['storage_bucket']
        service_account = CONFIG['dev_firebase']['service_account']
    except:
        # Default Configuration
        raise Exception('Could not get firebase dev information from config file.')

    # adapt this to your firebase setting
    config = {
        "apiKey": api_key,
        "authDomain": auth_domain,
        "databaseURL": database_url,
        "storageBucket": storage_bucket,
        # this is important if you want to login as admin
        "serviceAccount": SERVICE_ACCOUNT_KEY_PATH
    }

    print('use dev configuration: %s' % config)

    firebase = pyrebase.initialize_app(config)
    return firebase


# get the api_key
def get_api_key(tileserver):
    CONFIG = load_config()
    try:
        return CONFIG['imagery'][tileserver]['api_key']
    except KeyError:
        print('Could not find the API key for imagery tileserver {} in {}.'.format(tileserver, CONFIG_PATH))
        raise


# get tileserver url
def get_tileserver_url(tileserver):
    CONFIG = load_config()
    try:
        return CONFIG['imagery'][tileserver]['url']
    except KeyError:
        print('Could not find the url for imagery tileserver {} in {}.'.format(tileserver, CONFIG_PATH))
        raise


# get the import submission_key
def get_submission_key():
    CONFIG = load_config()
    try:
        return CONFIG['import']['submission_key']
    except KeyError:
        print("Couldn't find the submission key in {}".format(CONFIG_PATH))
        raise


class dev_psqlDB(object):
    # TODO: Delete this function after making sure <modus>
    # is not been used anymore
    _db_connection = None
    _db_cur = None

    def __init__(self):
        # try to load configuration from config file
        CONFIG = load_config()
        try:
            dbname = CONFIG['dev_psql']['database']
            user = CONFIG['dev_psql']['username']
            password = CONFIG['dev_psql']['password']
            host = CONFIG['dev_psql']['host']
            port = CONFIG['dev_psql']['port']
            # print('use configuration for psql as provided by config.json')
        except:
            # Default configuration
            raise Exception('Could not load psql dev info from the config file')

        self._db_connection = psycopg2.connect(
            database=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

    def query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def retr_query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        content = self._db_cur.fetchall()
        self._db_connection.commit()
        self._db_cur.close()
        return content

    def copy_from(self, file, table, sep='\t', null='\\N', size=8192, columns=None):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.copy_from(file, table, sep=sep, null='\\N', size=8192, columns=columns)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def __del__(self):
        # self._db_cur.close()
        self._db_connection.close()


class psqlDB(object):
    _db_connection = None
    _db_cur = None

    def __init__(self):
        # try to load configuration from config file
        CONFIG = load_config()
        try:
            dbname = CONFIG['psql']['database']
            user = CONFIG['psql']['username']
            password = CONFIG['psql']['password']
            host = CONFIG['psql']['host']
            port = CONFIG['psql']['port']  # print('use configuration for psql as provided by config.json')
        except:
            # Default configuration
            raise Exception('Could not load psql info from the config file')

        self._db_connection = psycopg2.connect(database=dbname, user=user, password=password, host=host, port=port)

    def query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def retr_query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        content = self._db_cur.fetchall()
        self._db_connection.commit()
        self._db_cur.close()
        return content

    def copy_from(self, file, table, sep='\t', null='\\N', size=8192, columns=None):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.copy_from(file, table, sep=sep, null='\\N', size=8192, columns=columns)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def __del__(self):
        # self._db_cur.close()
        self._db_connection.close()


class postgresDB(object):
    _db_connection = None
    _db_cur = None

    def __init__(self):
        # try to load configuration from config file
        CONFIG = load_config()
        try:
            dbname = CONFIG['psql']['database']
            user = CONFIG['psql']['username']
            password = CONFIG['psql']['password']
            host = CONFIG['psql']['host']
            port = CONFIG['psql']['port']  # print('use configuration for psql as provided by config.json')
        except:
            # Default configuration
            raise Exception('Could not load psql info from the config file')

        self._db_connection = psycopg2.connect(database=dbname, user=user, password=password, host=host, port=port)

    def query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def retr_query(self, query, data):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.execute(query, data)
        content = self._db_cur.fetchall()
        self._db_connection.commit()
        self._db_cur.close()
        return content

    def copy_from(self, file, table, sep='\t', null='\\N', size=8192, columns=None):
        self._db_cur = self._db_connection.cursor()
        self._db_cur.copy_from(file, table, sep=sep, null='\\N', size=8192, columns=columns)
        self._db_connection.commit()
        self._db_cur.close()
        return

    def __del__(self):
        # self._db_cur.close()
        self._db_connection.close()