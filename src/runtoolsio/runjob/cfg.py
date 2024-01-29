"""
Global configuration
For more information read: https://github.com/tarotools/taro-core/blob/master/docs/CONFIG.md

Implementation of config pattern:
https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
"""

import distutils.util
from enum import Enum, auto

import sys

from runtoolsio.runcore import util, paths
from runtoolsio.runcore.common import ConfigFileNotFoundError, RuntoolsException
from runtoolsio.runcore.util.attr import get_module_attributes


class LogMode(Enum):
    """
    This enum represents different logging modes that determine the behavior of loggers within the runtoolsio package.
    All loggers should be children of the `runtoolsio` logger, allowing all logging generated by the package to be
    enabled, forwarded to the root logger, or disabled as needed by setting this mode in `log` module.

    Attributes:
        ENABLED:
            In this mode, the 'runtoolsio' parent logger is enabled and configured handlers are added. As a result,
            all 'runtoolsio' logging is standardized and is handled independently of the client's root logger.
        PROPAGATE:
            In this mode, no handlers are attached and the log messages are propagated to the root logger.
            This allows the logs to be handled and formatted according to the root logger configuration.
        DISABLED:
            In this mode, all 'runtoolsio' logging is disabled.
    """

    ENABLED = auto()
    PROPAGATE = auto()
    DISABLED = auto()

    @staticmethod
    def from_value(val):
        if val is None:
            raise ValueError('Empty configuration value for log mode')
        if isinstance(val, LogMode):
            return val
        if isinstance(val, bool):
            return LogMode.ENABLED if val else LogMode.DISABLED
        if val.lower() == 'enabled' or val.lower() in util.TRUE_OPTIONS:
            return LogMode.ENABLED
        if val.lower() == 'disabled' or val.lower() in util.FALSE_OPTIONS:
            return LogMode.DISABLED
        if val.lower() == 'propagate':
            return LogMode.PROPAGATE
        raise ValueError('Unknown configuration value for logging: ' + str(val))


# ------------ DEFAULT VALUES ------------ #
DEF_LOG = LogMode.PROPAGATE
DEF_LOG_STDOUT_LEVEL = 'warn'
DEF_LOG_FILE_LEVEL = 'off'
DEF_LOG_FILE_PATH = None
DEF_LOG_TIMING = False

DEF_PERSISTENCE_ENABLED = True
DEF_PERSISTENCE_TYPE = 'sqlite'
DEF_PERSISTENCE_MAX_AGE = ''
DEF_PERSISTENCE_MAX_RECORDS = -1
DEF_PERSISTENCE_DATABASE = ''

DEF_LOCK_TIMEOUT = 10
DEF_LOCK_MAX_CHECK_TIME = 0.05

DEF_PLUGINS_ENABLED = False
DEF_PLUGINS_LOAD = ()

# ------------ CONFIG VALUES ------------ #
# !! UPDATE CONFIG.md when changes are made !! #

log_mode = DEF_LOG
log_stdout_level = DEF_LOG_STDOUT_LEVEL
log_file_level = DEF_LOG_FILE_LEVEL
log_file_path = DEF_LOG_FILE_PATH
log_timing = DEF_LOG_TIMING

persistence_enabled = DEF_PERSISTENCE_ENABLED
persistence_type = DEF_PERSISTENCE_TYPE
persistence_max_age = DEF_PERSISTENCE_MAX_AGE
persistence_max_records = DEF_PERSISTENCE_MAX_RECORDS
persistence_database = DEF_PERSISTENCE_DATABASE

lock_timeout_sec = DEF_LOCK_TIMEOUT
lock_max_check_time_sec = DEF_LOCK_MAX_CHECK_TIME

plugins_enabled = DEF_PLUGINS_ENABLED
plugins_load = DEF_PLUGINS_LOAD


def set_variables(**kwargs):
    module = sys.modules[__name__]
    current_attrs = get_module_attributes(module)

    for name, value in kwargs.items():
        cur_value = current_attrs[name]
        if type(value) == type(cur_value):
            value_to_set = value
        elif isinstance(cur_value, LogMode):  # Must be before bool or str as these types are supported by LogMode parse
            value_to_set = LogMode.from_value(value)
        elif isinstance(cur_value, bool):  # First bool than int, as bool is int..
            value_to_set = distutils.util.strtobool(value)
        elif isinstance(cur_value, int):
            value_to_set = int(value)
        elif isinstance(cur_value, tuple):
            value_to_set = tuple(value)
        else:
            raise TypeError(f'Cannot convert value {value} to {type(cur_value)}')

        setattr(module, name, value_to_set)


def set_minimal_config():
    global log_mode, log_stdout_level, log_file_level, log_file_path, log_timing
    global persistence_enabled, persistence_type, persistence_max_age, persistence_max_records, persistence_database
    global lock_timeout_sec, lock_max_check_time_sec
    global plugins_enabled, plugins_load

    log_mode = LogMode.ENABLED
    log_stdout_level = 'warn'
    log_file_level = 'off'
    log_file_path = None
    log_timing = False

    persistence_enabled = False
    persistence_type = 'sqlite'
    persistence_max_age = ''
    persistence_max_records = -1
    persistence_database = ''

    lock_timeout_sec = 10000
    lock_max_check_time_sec = 50

    plugins_enabled = False
    plugins_load = ()


loaded_config_path = None


def load_from_file(config=None):
    config_path = util.expand_user(config) if config else paths.lookup_config_file()
    try:
        flatten_cfg = util.read_toml_file_flatten(config_path)
    except FileNotFoundError:
        # Must be the explicit `config` as `lookup_config_file` already raises this exception
        raise ConfigFileNotFoundError(config)

    set_variables(**flatten_cfg)

    global loaded_config_path
    loaded_config_path = config_path


def copy_default_config_to_search_path(overwrite: bool):
    cfg_to_copy = paths.default_config_file_path()
    # Copy to first dir in search path
    # TODO Specify where to copy the file - do not use XDG search path
    copy_to = paths.taro_config_file_search_path(exclude_cwd=True)[0] / paths.CONFIG_FILE
    try:
        util.copy_resource(cfg_to_copy, copy_to, overwrite)
        return copy_to
    except FileExistsError as e:
        raise ConfigFileAlreadyExists(str(e)) from e


class ConfigFileAlreadyExists(RuntoolsException, FileExistsError):
    pass
