# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
import os
from datetime import datetime

from boto3.session import Session
import botocore.session

from pyathena.converter import TypeConverter
from pyathena.cursor import Cursor
from pyathena.error import NotSupportedError
from pyathena.formatter import ParameterFormatter


_logger = logging.getLogger(__name__)


def get_connection(**kwargs):
    """
    Using the botocore API we can not use the Athena std. mechanism to store Athena's
    query results. We need to mimic the std. mechanism as close as possible here.
    http://docs.aws.amazon.com/athena/latest/ug/querying.html

    :return: pyathena connection with the output_location set
    """
    # some helpers
    def get_client(session, service_name, **kwargs):
        return session.create_client(service_name, **kwargs)

    def get_region(session):
        """Get region from the session."""
        return session.get_config_variable('region')

    def get_account_id(session):
        """Get account id using session."""
        sts = get_client(session, 'sts')
        return sts.get_caller_identity()["Account"]

    session = botocore.session.get_session(**kwargs)

    date = datetime.now()
    output_location = 's3://aws-athena-query-results-%s-%s/jupyter-athena-sql/%d/%02d/%02d/' % (
        get_account_id(session), get_region(session), date.year, date.month, date.day)

    return Connection(botocore_session=session, s3_staging_dir=output_location, **kwargs)


class Connection(object):

    _ENV_S3_STAGING_DIR = 'AWS_ATHENA_S3_STAGING_DIR'

    def __init__(self, botocore_session=None, s3_staging_dir=None, region_name=None, schema_name='default',
            poll_interval=1, encryption_option=None, kms_key=None, profile_name=None,
            converter=None, formatter=None,
            retry_exceptions=('ThrottlingException', 'TooManyRequestsException'),
            retry_attempt=5, retry_multiplier=1,
            retry_max_delay=1800, retry_exponential_base=2,
            cursor_class=Cursor, **kwargs):
        if s3_staging_dir:
            self.s3_staging_dir = s3_staging_dir
        else:
            self.s3_staging_dir = os.getenv(self._ENV_S3_STAGING_DIR, None)
        assert self.s3_staging_dir, 'Required argument `s3_staging_dir` not found.'
        assert schema_name, 'Required argument `schema_name` not found.'
        self.region_name = region_name
        self.schema_name = schema_name
        self.poll_interval = poll_interval
        self.encryption_option = encryption_option
        self.kms_key = kms_key

        # we use the botocore_session we created earlier
        session = Session(botocore_session=botocore_session)
        self._client = session.client('athena', **kwargs)

        self._converter = converter if converter else TypeConverter()
        self._formatter = formatter if formatter else ParameterFormatter()

        self.retry_exceptions = retry_exceptions
        self.retry_attempt = retry_attempt
        self.retry_multiplier = retry_multiplier
        self.retry_max_delay = retry_max_delay
        self.retry_exponential_base = retry_exponential_base

        self.cursor_class = cursor_class

    def __enter__(self):
        return self.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def cursor(self, cursor=None, **kwargs):
        if not cursor:
            cursor = self.cursor_class
        return cursor(self._client, self.s3_staging_dir, self.schema_name, self.poll_interval,
                      self.encryption_option, self.kms_key, self._converter, self._formatter,
                      self.retry_exceptions, self.retry_attempt, self.retry_multiplier,
                      self.retry_max_delay, self.retry_exponential_base, **kwargs)

    def close(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        raise NotSupportedError
