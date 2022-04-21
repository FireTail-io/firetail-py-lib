import logging
import pathlib
import re
import typing as t
from contextvars import ContextVar

from starlette.responses import RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.routing import Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from pointsecio.apis import AbstractSwaggerUIAPI
from pointsecio.jsonifier import JSONEncoder, Jsonifier
from pointsecio.utils import yamldumper

from .base import AppMiddleware

logger = logging.getLogger('pointsecio.middleware.swagger_ui')


_original_scope: ContextVar[Scope] = ContextVar('SCOPE')


class SwaggerUIMiddleware(AppMiddleware):

    def __init__(self, app: ASGIApp) -> None:
        """Middleware that hosts a swagger UI.

        :param app: app to wrap in middleware.
        """
        self.app = app
        # Set default to pass unknown routes to next app
        self.router = Router(default=self.default_fn)

    def add_api(
            self,
            specification: t.Union[pathlib.Path, str, dict],
            base_path: t.Optional[str] = None,
            arguments: t.Optional[dict] = None,
            **kwargs
    ) -> None:
        """Add an API to the router based on a OpenAPI spec.

        :param specification: OpenAPI spec as dict or path to file.
        :param base_path: Base path where to add this API.
        :param arguments: Jinja arguments to replace in the spec.
        """
        api = SwaggerUIAPI(specification, base_path=base_path, arguments=arguments,
                           default=self.default_fn, **kwargs)
        self.router.mount(api.base_path, app=api.router)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        _original_scope.set(scope.copy())
        await self.router(scope, receive, send)

    async def default_fn(self, _scope: Scope, receive: Receive, send: Send) -> None:
        """
        Callback to call next app as default when no matching route is found.

        Unfortunately we cannot just pass the next app as default, since the router manipulates
        the scope when descending into mounts, losing information about the base path. Therefore,
        we use the original scope instead.

        This is caused by https://github.com/encode/starlette/issues/1336.
        """
        original_scope = _original_scope.get()
        await self.app(original_scope, receive, send)


class SwaggerUIAPI(AbstractSwaggerUIAPI):

    def __init__(self, *args, default: ASGIApp, **kwargs):
        self.router = Router(default=default)

        super().__init__(*args, **kwargs)

        self._templates = Jinja2Templates(
            directory=str(self.options.openapi_console_ui_from_dir)
        )

    @staticmethod
    def normalize_string(string):
        return re.sub(r"[^a-zA-Z0-9]", "_", string.strip("/"))

    def _base_path_for_prefix(self, request):
        """
        returns a modified basePath which includes the incoming request's
        path prefix.
        """
        base_path = self.base_path
        if not request.url.path.startswith(self.base_path):
            prefix = request.url.path.split(self.base_path)[0]
            base_path = prefix + base_path
        return base_path

    def _spec_for_prefix(self, request):
        """
        returns a spec with a modified basePath / servers block
        which corresponds to the incoming request path.
        This is needed when behind a path-altering reverse proxy.
        """
        base_path = self._base_path_for_prefix(request)
        return self.specification.with_base_path(base_path).raw

    def add_openapi_json(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        # logger.info(
        #     "Adding spec json: %s/%s", self.base_path, self.options.openapi_spec_path
        # )
        self.router.add_route(
            methods=["GET"],
            path=self.options.openapi_spec_path,
            endpoint=self._get_openapi_json,
        )

    def add_openapi_yaml(self):
        """
        Adds openapi json to {base_path}/openapi.json
             (or {base_path}/swagger.json for swagger2)
        """
        if not self.options.openapi_spec_path.endswith("json"):
            return

        openapi_spec_path_yaml = self.options.openapi_spec_path[: -len("json")] + "yaml"
        logger.debug("Adding spec yaml: %s/%s", self.base_path, openapi_spec_path_yaml)
        self.router.add_route(
            methods=["GET"],
            path=openapi_spec_path_yaml,
            endpoint=self._get_openapi_yaml,
        )

    async def _get_openapi_json(self, request):
        return StarletteResponse(
            content=self.jsonifier.dumps(self._spec_for_prefix(request)),
            status_code=200,
            media_type="application/json",
        )

    async def _get_openapi_yaml(self, request):
        return StarletteResponse(
            content=yamldumper(self._spec_for_prefix(request)),
            status_code=200,
            media_type="text/yaml",
        )

    def add_swagger_ui(self):
        """
        Adds swagger ui to {base_path}/ui/
        """
        console_ui_path = self.options.openapi_console_ui_path.strip().rstrip("/")
        logger.debug("Adding swagger-ui: %s%s/", self.base_path, console_ui_path)

        for path in (
                console_ui_path + "/",
                console_ui_path + "/index.html",
        ):
            self.router.add_route(
                methods=["GET"], path=path, endpoint=self._get_swagger_ui_home
            )

        if self.options.openapi_console_ui_config is not None:
            self.router.add_route(
                methods=["GET"],
                path=console_ui_path + "/swagger-ui-config.json",
                endpoint=self._get_swagger_ui_config,
            )

        # we have to add an explicit redirect instead of relying on the
        # normalize_path_middleware because we also serve static files
        # from this dir (below)

        async def redirect(_request):
            return RedirectResponse(url=self.base_path + console_ui_path + "/")

        self.router.add_route(methods=["GET"], path=console_ui_path, endpoint=redirect)

        # this route will match and get a permission error when trying to
        # serve index.html, so we add the redirect above.
        self.router.mount(
            path=console_ui_path,
            app=StaticFiles(directory=str(self.options.openapi_console_ui_from_dir)),
            name="swagger_ui_static",
        )

    async def _get_swagger_ui_home(self, req):
        base_path = self._base_path_for_prefix(req)
        template_variables = {
            "request": req,
            "openapi_spec_url": (base_path + self.options.openapi_spec_path),
            **self.options.openapi_console_ui_index_template_variables,
        }
        if self.options.openapi_console_ui_config is not None:
            template_variables["configUrl"] = "swagger-ui-config.json"

        return self._templates.TemplateResponse("index.j2", template_variables)

    async def _get_swagger_ui_config(self, request):
        return StarletteResponse(
            status_code=200,
            media_type="application/json",
            content=self.jsonifier.dumps(self.options.openapi_console_ui_config),
        )

    @classmethod
    def _set_jsonifier(cls):
        cls.jsonifier = Jsonifier(cls=JSONEncoder)
