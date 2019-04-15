# Development

In this document some tips and workflows for development and hosting are loosely collected. Those are independend of Docker (production setup).


## Development setup (without Docker)

- Install GDAL
- Setup virtual environment with system-site-packages enabled (To get access to GDAL)
    - `python3 -m venv --system-site-packages venv`
- Activate virtual environment
    - `source venv/bin/activate`
- Install mapswipe_workers
    - `pip install -e .`
- Setup and install Mapswipe Workers as described in [setup.md](setup.md).
    - Ignore Docker related steps
- Setup a postgres instance
    - Use simply the Docker image of Mapwsipe Workers (`docker-compose up -d postgres`)
    - Or set up your own using the `postgres_create_tables.sql` file in the `docker/` folder


## Configuration path and data path

Mapswipe Workers will look for a configuration file and the Service Account Key at `$HOME/.config/mapswipe_workers/` (The `$XDG_CONFIG_HOME` variable will be respected)

1. Move the example configuration (`config/configuration.json`)
    - `mkdir ~/.config/mapswipe_workers/`
    - `mv config/configuration.json ~/.config/mapswipe_workers/configuration.json`
2. Rename downloaded Service Account Key to `serviceAccountKey.json` and move it to the above described configuration directory
3. Provide a environment file

Logs and data of Mapswipe Workers are stored at following locations:
- logs: `/var/log/mapswipe.log`
- data: `/var/lib/mapswipe/`

Depending on user permissions you have to change ownership/permissions (chown) of those directories for the application to work.


## Testing

Test order:

1. `test_initialize.py`
2. `test_import.py`
3. `test_mock_results.py`
4. `test_transfer_results.py`
5. `test_update.py`
6. `test_export.py`


## Logging

Mapswipe workers logs are generated using the Python logging module of the standard library (See [Official docs](https://docs.python.org/3/library/logging.html) or this [Tutorial](https://realpython.com/python-logging/#the-logging-module). The configuration file of the logging module is located at `mapswipe_workers/logging.cfg`. With this configuration a logger object is generated in the `definitions` module (`mapswipe_workers.definitions.py`) and is imported in other modules to write logs.

```python
from mapswipe_workers.definitions import logger
logger.info('information')
logger.waring('warning')

# Include stack trace in the log
try:
    print(something)
except Exception:
    logger.exception('something')
```

Default logging level is Warning. To change the logging level edit the configuration (`mapswipe_workers/logging.cfg`).

Per default logging of third-party packages is disabled. To change this edit the definition module (`mapswipe_workers/defintions.md`). Set the `disable_existing_loggers` parameter of the `logging.config.fileConfig()` function to False.


## Firebase Functions

Firebase functions are used by Mapswipe Workers to calculate or increment attribute values wich are needed by the Mapswipe App. This includes at the moment:
- project.progress
- group.progress
- group.resultCounter
- group.resultRequiredCounter
- user.contributionCounter
- user.distance

To contribute changes to the Firebase Functions please refer to the official (Guide on Cloud Function for Firebase)[https://firebase.google.com/docs/functions/get-started] on how to setup development enviroment and on how to deploy functions to the Firebase instance. For more information refer to the official (Reference on Cloud Function for Firebase)[https://firebase.google.com/docs/reference/functions/]. For example function take a look at this (GitHub repository)[https://github.com/firebase/functions-samples].


## Database Backup

### Firebase

**Manual Backup**
- curl https://<instance>.firebaseio.com/.json?format=export
- ref: https://stackoverflow.com/questions/27910784/is-it-possible-to-backup-firebase-db


### Postgres

**Manual Backup**
- Backup database in compressed splited files of specified size:
    - `pg_dump -U mapswipe -d mapswipe -h localhost -p 5432 | gzip | split -b 100m - mapswipe.pgsql.gz`
    - ref: https://www.postgresql.org/docs/9.1/backup-dump.html
- Copy the backup to your local machine when logged into your local machine:
    - `scp username@ipadress:mapswipe.pgsql.gz* /path/to/destination`
    - ref: https://unix.stackexchange.com/questions/106480/how-to-copy-files-from-one-machine-to-another-using-ssh
- Restore database backup from multiple compressed files
    - `cat mapswipe.pgsql.gz* | gunzip | psql -U mapswipe -d mapswipe -h localhost -p 5432`