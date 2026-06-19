from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.developer_app import ApiKey, AppStatus, AppType, DeveloperApp, DeveloperTier
from ..entities.plugin import Plugin, PluginStatus, PluginType, PriceModel


class DeveloperPortalService:
    def __init__(self) -> None:
        self._developers: dict[str, dict[str, Any]] = {}
        self._apps: dict[str, DeveloperApp] = {}
        self._api_keys: dict[str, ApiKey] = {}

    def register_developer(
        self,
        tenant_id: str,
        developer_name: str,
        email: str,
        tier: DeveloperTier = DeveloperTier.FREE,
    ) -> dict[str, Any]:
        developer_id = f"dev-{uuid.uuid4().hex[:12]}"
        self._developers[developer_id] = {
            "developer_id": developer_id,
            "tenant_id": tenant_id,
            "developer_name": developer_name,
            "email": email,
            "tier": tier.value,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._developers[developer_id]

    def create_api_key(
        self,
        developer_id: str,
        scopes: list[str] | None = None,
        rate_limit: int = 1000,
    ) -> ApiKey | None:
        dev = self._developers.get(developer_id)
        if not dev:
            return None

        key_id = str(uuid.uuid4())
        key_prefix = f"afk_{uuid.uuid4().hex[:8]}"
        api_key = ApiKey(
            key_id=key_id,
            key_prefix=key_prefix,
            scopes=scopes or ["read"],
            rate_limit=rate_limit,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._api_keys[key_id] = api_key
        return api_key

    def submit_app(
        self,
        tenant_id: str,
        developer_id: str,
        name: str,
        description: str,
        app_type: str = "integration",
    ) -> DeveloperApp | None:
        dev = self._developers.get(developer_id)
        if not dev:
            return None

        try:
            atype = AppType(app_type)
        except ValueError:
            atype = AppType.INTEGRATION

        app = DeveloperApp(
            tenant_id=tenant_id,
            developer_id=developer_id,
            name=name,
            description=description,
            app_type=atype,
        )
        app.submit()
        self._apps[app.id] = app
        return app

    def publish_app(self, app_id: str) -> DeveloperApp | None:
        app = self._apps.get(app_id)
        if not app:
            return None
        if app.status == AppStatus.SUBMITTED:
            app.approve()
        app.publish()
        return app

    def track_api_usage(self, app_id: str) -> dict[str, Any] | None:
        app = self._apps.get(app_id)
        if not app:
            return None

        app.update_usage(
            calls=random.randint(100, 50000),
            errors=random.uniform(0.001, 0.05),
            latency=random.uniform(20, 200),
        )

        return {
            "app_id": app_id,
            "usage_stats": app.usage_stats.to_dict(),
            "tracked_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_app(self, app_id: str) -> DeveloperApp | None:
        return self._apps.get(app_id)


class PluginMarketplaceService:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._installed: dict[str, list[str]] = {}

    def submit_plugin(
        self,
        tenant_id: str,
        developer_id: str,
        name: str,
        description: str,
        plugin_type: str = "visualization",
        price_model: str = "free",
    ) -> Plugin:
        try:
            ptype = PluginType(plugin_type)
        except ValueError:
            ptype = PluginType.VISUALIZATION
        try:
            pmodel = PriceModel(price_model)
        except ValueError:
            pmodel = PriceModel.FREE

        plugin = Plugin(
            tenant_id=tenant_id,
            developer_id=developer_id,
            name=name,
            description=description,
            plugin_type=ptype,
            price_model=pmodel,
        )
        self._plugins[plugin.id] = plugin
        return plugin

    def review_and_publish(self, plugin_id: str) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None
        plugin.approve_and_publish()
        return plugin

    def list_plugins(
        self,
        plugin_type: str | None = None,
        search: str | None = None,
    ) -> list[Plugin]:
        plugins = [p for p in self._plugins.values() if p.status == PluginStatus.PUBLISHED]
        if plugin_type:
            plugins = [p for p in plugins if p.plugin_type.value == plugin_type]
        if search:
            search_lower = search.lower()
            plugins = [p for p in plugins if search_lower in p.name.lower() or search_lower in p.description.lower()]
        return sorted(plugins, key=lambda p: p.install_count, reverse=True)

    def install_plugin(self, tenant_id: str, plugin_id: str) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin or plugin.status != PluginStatus.PUBLISHED:
            return None

        plugin.increment_install()
        if tenant_id not in self._installed:
            self._installed[tenant_id] = []
        self._installed[tenant_id].append(plugin_id)
        return plugin

    def uninstall_plugin(self, tenant_id: str, plugin_id: str) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None

        plugin.decrement_install()
        if tenant_id in self._installed:
            self._installed[tenant_id] = [pid for pid in self._installed[tenant_id] if pid != plugin_id]
        return plugin

    def rate_plugin(self, plugin_id: str, score: float) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None
        plugin.add_rating(min(max(score, 1.0), 5.0))
        return plugin

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def get_installed(self, tenant_id: str) -> list[Plugin]:
        ids = self._installed.get(tenant_id, [])
        return [self._plugins[pid] for pid in ids if pid in self._plugins]