# -*- coding: utf-8 -*-
"""Runs SQL queries on AWS athena.
"""
from IPython.core.magic import Magics, magics_class, cell_magic, line_magic, needs_local_scope
try:
    from traitlets.config.configurable import Configurable
    from traitlets import Bool, Int, Unicode
except ImportError:
    from IPython.config.configurable import Configurable
    from IPython.utils.traitlets import Bool, Int, Unicode

from pandas import read_sql

from .connection import get_connection


@magics_class
class Athena(Magics, Configurable):
    """
    Runs SQL statement on AWS athena, specified by s3:// connect string.

    Provides the %%athena magic.
    """

    def __init__(self, shell):
        Configurable.__init__(self, config=shell.config)
        Magics.__init__(self, shell=shell)

        # Add ourself to the list of module configurable via %config
        self.shell.configurables.append(self)
        self.conn = None

    @needs_local_scope
    @line_magic('athena')
    @cell_magic('athena')
    def execute(self, line, cell='', local_ns={}):
        """Runs SQL statement against a database, specified by SQLAlchemy connect string.

        If no database connection has been established, first word
        should be a SQLAlchemy connection string, or the user@db name
        of an established connection.

        Examples::
          %athena s3://my-bucket/folder

          %athena SELECT * FROM mydatabase.mytable

          %%athena
          DROP TABLE mytable
        """
        ipt = ('%s\n%s' % (line, cell)).strip()
        try:
            # I took away some of the magic mainly by making the program flow
            # explicit. I hope that is ok?!
            df = read_sql(ipt, get_connection())
            if not df.empty:
                return df
        except Exception as e:
            print(e)
            return None


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(Athena)


def unload_ipython_extension(ip):
    """Unload the extension in IPython."""
    if 'Athena' in ip.magics_manager.registry:
        del ip.magics_manager.registry['Athena']
    if 'Athena' in ip.config:
        del ip.config['Athena']