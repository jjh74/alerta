import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Dict, Iterable, Union

from flask import Flask
from pkg_resources import (DistributionNotFound, iter_entry_points,
                           load_entry_point)

LOG = logging.getLogger('alerta.plugins')

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa
    from alerta.plugins import PluginBase  # noqa


class Plugins:

    def __init__(self) -> None:
        self.app = None
        self.plugins = OrderedDict()  # type: OrderedDict[str, PluginBase]
        self.rules = None

    def register(self, app: Flask) -> None:
        self.app = app
        entry_points = {}
        for ep in iter_entry_points('alerta.plugins'):
            LOG.debug("Server plugin '{}' found.".format(ep.name))
            entry_points[ep.name] = ep

        for name in self.app.config['PLUGINS']:
            try:
                plugin = entry_points[name].load()
                if plugin:
                    self.plugins[name] = plugin()
                    LOG.info("Server plugin '{}' loaded.".format(name))
            except Exception as e:
                LOG.error("Failed to load plugin '{}': {}".format(name, str(e)))
        LOG.info('All server plugins enabled: {}'.format(', '.join(self.plugins.keys())))
        try:
            self.rules = load_entry_point('alerta-routing', 'alerta.routing', 'rules')  # type: ignore
        except (DistributionNotFound, ImportError):
            LOG.info('No plugin routing rules found. All plugins will be evaluated.')

    def routing(self, alert: 'Alert') -> Union[Iterable['PluginBase'], Dict[str, Any]]:
        try:
            if self.plugins and self.rules:
                return self.rules(alert, self.plugins), self.app.config
        except Exception as e:
            LOG.warning('Plugin routing rules failed: {}'.format(e))

        return self.plugins.values(), self.app.config
