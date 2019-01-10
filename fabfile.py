from fabric.api import run
from fabric.api import env, hide, local, settings, abort, sudo, warn_only
import os

def check_postgresql():
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        res = local('dpkg -l | grep ii | grep postgresql', capture=True)
        if res.failed:
            abort("Postgresql not installed!")
 
def check_virtualenv():
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        if not os.environ.get('VIRTUAL_ENV'): 
            abort("You're not running a virtualenv!!!")

def check_python_version():
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        res = local("python --version", capture=True)
        if res.failed:
            abort("Python not installed! Get the 3.4 version ")

# set a local dev env
def set_local_settings():
    with settings(hide('stdout', 'stderr', 'warnings'), warn_only=True):
        local('cp psr/settings/local_settings.py.ex psr/settings/local_settings.py', capture=True)

def install_pip_pkgs():
    with settings(hide('stdout', 'stderr', 'warnings'), warn_only=True):
        local('pip install -r requirements.txt', capture=True)

def set_local_env():
    check_virtualenv()
    check_python_version()
    #set_local_settings()
    install_pip_pkgs()
    configure_pg()

# PSQL
def _run_as_pg(command):
    return local('sudo -u postgres %s' % command)

def pg_user_exists():
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        res = _run_as_pg('psql -c "SELECT COUNT(*) FROM pg_user WHERE usename = %s;"' % ('psr_dev'))
    return (res == "1")

def pg_database_exists():
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        res = _run_as_pg('psql -c "SELECT COUNT(*) FROM pg_database WHERE datname = %s;"' % ('psr_dev'))
    return (res == "1")

def pg_create_user():
    _run_as_pg('psql -c "CREATE USER %s WITH PASSWORD \'%s\';"' % ('psr_dev','psr_dev'))

def pg_drop_user():
    _run_as_pg('psql -c "DROP USER %s;"' % ('psr_dev'))

def pg_create_database():
    _run_as_pg('psql -c "CREATE DATABASE %s;"' % ('psr_dev'))

def pg_drop_database():
    _run_as_pg('psql -c "DROP DATABASE %s;"' % ('psr_dev'))

def pg_grant_priv():
    _run_as_pg('psql -c "GRANT ALL PRIVILEGES ON DATABASE %s TO %s;"' % ('psr_dev','psr_dev'))

def configure_pg():
    check_postgresql()
    if not pg_user_exists():
        if not pg_database_exists():
            set_multidb()

#-----------

def pg_create_multidb():
    _run_as_pg('psql -c "CREATE DATABASE %s;"' % ('psr_dev'))
    _run_as_pg('psql -c "CREATE DATABASE %s;"' % ('psr_ca_dev'))
    _run_as_pg('psql -c "CREATE DATABASE %s;"' % ('psr_us_dev'))

def pg_drop_multidb():
    _run_as_pg('psql -c "DROP DATABASE %s;"' % ('psr_dev'))
    _run_as_pg('psql -c "DROP DATABASE %s;"' % ('psr_ca_dev'))
    _run_as_pg('psql -c "DROP DATABASE %s;"' % ('psr_us_dev'))

def pg_create_multidb_user():
    _run_as_pg('psql -c "CREATE USER %s WITH PASSWORD \'%s\';"' % ('psr_dev','psr_dev'))
    _run_as_pg('psql -c "CREATE USER %s WITH PASSWORD \'%s\';"' % ('psr_ca_dev','psr_ca_dev'))
    _run_as_pg('psql -c "CREATE USER %s WITH PASSWORD \'%s\';"' % ('psr_us_dev','psr_us_dev'))

def pg_drop_multidb_user():
    _run_as_pg('psql -c "DROP USER %s;"' % ('psr_dev'))
    _run_as_pg('psql -c "DROP USER %s;"' % ('psr_ca_dev'))
    _run_as_pg('psql -c "DROP USER %s;"' % ('psr_us_dev'))

def pg_grant_priv_multidb():
    _run_as_pg('psql -c "GRANT ALL PRIVILEGES ON DATABASE %s TO %s;"' % ('psr_dev','psr_dev'))
    _run_as_pg('psql -c "GRANT ALL PRIVILEGES ON DATABASE %s TO %s;"' % ('psr_ca_dev','psr_ca_dev'))
    _run_as_pg('psql -c "GRANT ALL PRIVILEGES ON DATABASE %s TO %s;"' % ('psr_us_dev','psr_us_dev'))


def set_multidb():
    pg_create_multidb()
    pg_create_multidb_user()
    pg_grant_priv_multidb()

def drop_multidb():
    pg_drop_multidb()
    pg_drop_multidb_user()
    


#-----------
