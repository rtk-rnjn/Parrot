from dataclasses import dataclass


@dataclass(frozen=True)
class DocSite:
    url: str
    aliases: tuple[str, ...] = ()
    kind: str | None = None  # force a loader: sphinx | mkdocs | llms | sitemap

    packages: tuple[str, ...] = ()
    fallbacks: tuple[str, ...] = ()


SITES: dict[str, DocSite] = {
    "discord": DocSite("https://discordpy.readthedocs.io/en/latest", ("dpy", "discord.py"), packages=("discord",), kind="sphinx"),
    "python": DocSite("https://docs.python.org/3", ("py",)),
    "aiohttp": DocSite("https://docs.aiohttp.org/en/latest", packages=("aiohttp",), kind="sphinx"),
    "requests": DocSite("https://requests.readthedocs.io/en/latest", ("req", "request"), packages=("requests",), kind="sphinx"),
    "numpy": DocSite("https://numpy.org/doc/stable", ("np",), packages=("numpy",), kind="sphinx"),
    "pandas": DocSite("https://pandas.pydata.org/docs", ("pd",), packages=("pandas",), kind="sphinx"),
    "matplotlib": DocSite("https://matplotlib.org/stable", ("plt", "mat", "matlab"), packages=("matplotlib", "mpl_toolkits"), kind="sphinx"),
    "pil": DocSite("https://pillow.readthedocs.io/en/stable", ("pillow",), packages=("PIL",), kind="sphinx"),
    "flask": DocSite("https://flask.palletsprojects.com/en/latest", packages=("flask",), kind="sphinx"),
    "pymongo": DocSite("https://pymongo.readthedocs.io/en/stable", ("mongo", "pym"), packages=("pymongo", "bson", "gridfs"), kind="sphinx"),
    "django": DocSite("https://docs.djangoproject.com/en/stable", packages=("django",), kind="sphinx"),
    "sqlalchemy": DocSite("https://docs.sqlalchemy.org/en/20", ("sa",), packages=("sqlalchemy",), kind="sphinx"),
    "fastapi": DocSite("https://fastapi.tiangolo.com", kind="mkdocs", packages=("fastapi",), fallbacks=("llms", "sitemap")),
    "pydantic": DocSite("https://docs.pydantic.dev/latest", kind="mkdocs", packages=("pydantic",), fallbacks=("llms", "sitemap")),
    # Core development and system utilities.
    "cryptography": DocSite("https://cryptography.io/en/latest", packages=("cryptography",), kind="sphinx"),
    "paramiko": DocSite("https://docs.paramiko.org/en/stable", packages=("paramiko",), kind="sphinx"),
    "fabric": DocSite("https://docs.fabfile.org/en/stable", packages=("fabric",), kind="sphinx"),
    "invoke": DocSite("https://docs.pyinvoke.org/en/stable", packages=("invoke",), kind="sphinx"),
    "cffi": DocSite("https://cffi.readthedocs.io/en/stable", packages=("cffi",), kind="sphinx"),
    "cython": DocSite("https://cython.readthedocs.io/en/latest", packages=("Cython",), kind="sphinx"),
    "gevent": DocSite("https://www.gevent.org", packages=("gevent",), kind="sphinx"),
    "twisted": DocSite("https://docs.twisted.org/en/stable", packages=("twisted",), kind="sphinx"),
    "greenlet": DocSite("https://greenlet.readthedocs.io/en/latest", packages=("greenlet",), kind="sphinx"),
    "pyinstaller": DocSite("https://pyinstaller.org/en/stable", packages=("PyInstaller",), kind="sphinx"),
    "psutil": DocSite("https://psutil.readthedocs.io/en/latest", packages=("psutil",), kind="sphinx"),
    "pyserial": DocSite("https://pyserial.readthedocs.io/en/latest", ("serial",), packages=("serial",), kind="sphinx"),
    # Security and authentication.
    "pyjwt": DocSite("https://pyjwt.readthedocs.io/en/stable", ("jwt",), packages=("jwt",), kind="sphinx"),
    "bcrypt": DocSite("https://bcrypt.readthedocs.io/en/stable", packages=("bcrypt",), kind="sphinx"),
    "passlib": DocSite("https://passlib.readthedocs.io/en/stable", packages=("passlib",), kind="sphinx"),
    "certifi": DocSite("https://certifiio.readthedocs.io/en/latest", packages=("certifi",), kind="sphinx"),
    # File handling and document processing.
    "openpyxl": DocSite("https://openpyxl.readthedocs.io/en/stable", packages=("openpyxl",), kind="sphinx"),
    "xlsxwriter": DocSite("https://xlsxwriter.readthedocs.io", packages=("xlsxwriter",), kind="sphinx"),
    "python-docx": DocSite("https://python-docx.readthedocs.io/en/latest", ("docx",), packages=("docx",), kind="sphinx"),
    "pypdf": DocSite("https://pypdf.readthedocs.io/en/stable", packages=("pypdf",), kind="sphinx"),
    "lxml": DocSite("https://lxml.de", packages=("lxml",), kind="sphinx"),
    "python-magic": DocSite("https://python-magic.readthedocs.io/en/latest", ("magic",), packages=("magic",), kind="sphinx"),
    "fsspec": DocSite("https://filesystem-spec.readthedocs.io/en/latest", packages=("fsspec",), kind="sphinx"),
    # AWS and cloud SDKs.
    "boto3": DocSite("https://boto3.amazonaws.com/v1/documentation/api/latest", packages=("boto3",), kind="sphinx"),
    "botocore": DocSite("https://botocore.amazonaws.com/v1/documentation/api/latest", packages=("botocore",), kind="sphinx"),
    "s3fs": DocSite("https://s3fs.readthedocs.io/en/latest", packages=("s3fs",), kind="sphinx"),
    "aiobotocore": DocSite("https://aiobotocore.aio-libs.org/en/stable", packages=("aiobotocore",), kind="sphinx"),
    # Templates and web utilities.
    "jinja2": DocSite("https://jinja.palletsprojects.com/en/stable", packages=("jinja2",), kind="sphinx"),
    "werkzeug": DocSite("https://werkzeug.palletsprojects.com/en/stable", packages=("werkzeug",), kind="sphinx"),
    "itsdangerous": DocSite("https://itsdangerous.palletsprojects.com/en/stable", packages=("itsdangerous",), kind="sphinx"),
    "pygments": DocSite("https://pygments.org/docs", packages=("pygments",), kind="sphinx"),
    "blinker": DocSite("https://blinker.readthedocs.io/en/stable", packages=("blinker",), kind="sphinx"),
    # HTTP, networking and scraping
    "urllib3": DocSite("https://urllib3.readthedocs.io/en/stable", packages=("urllib3",), kind="sphinx"),
    "websockets": DocSite("https://websockets.readthedocs.io/en/stable", packages=("websockets",), kind="sphinx"),
    "anyio": DocSite("https://anyio.readthedocs.io/en/stable", packages=("anyio",), kind="sphinx"),
    "trio": DocSite("https://trio.readthedocs.io/en/stable", packages=("trio",), kind="sphinx"),
    "scrapy": DocSite("https://docs.scrapy.org/en/latest", packages=("scrapy",), kind="sphinx"),
    "websocket-client": DocSite("https://websocket-client.readthedocs.io/en/latest", packages=("websocket",), kind="sphinx"),
    "asyncpg": DocSite("https://magicstack.github.io/asyncpg/current", packages=("asyncpg",), kind="sphinx"),
    # Data science
    "scipy": DocSite("https://docs.scipy.org/doc/scipy", packages=("scipy",), kind="sphinx"),
    "sklearn": DocSite("https://scikit-learn.org/stable", ("scikit-learn",), packages=("sklearn",), kind="sphinx"),
    "seaborn": DocSite("https://seaborn.pydata.org", packages=("seaborn",), kind="sphinx"),
    "sympy": DocSite("https://docs.sympy.org/latest", packages=("sympy",), kind="sphinx"),
    "networkx": DocSite("https://networkx.org/documentation/stable", packages=("networkx",), kind="sphinx"),
    "statsmodels": DocSite("https://www.statsmodels.org/stable", packages=("statsmodels",), kind="sphinx"),
    "numba": DocSite("https://numba.readthedocs.io/en/stable", packages=("numba",), kind="sphinx"),
    "dask": DocSite("https://docs.dask.org/en/stable", packages=("dask",), kind="sphinx"),
    "xarray": DocSite("https://docs.xarray.dev/en/stable", packages=("xarray",), kind="sphinx"),
    "pyarrow": DocSite("https://arrow.apache.org/docs/python", packages=("pyarrow",), kind="sphinx"),
    # Testing and code quality
    "pytest": DocSite("https://docs.pytest.org/en/stable", packages=("pytest",), kind="sphinx"),
    "coverage": DocSite("https://coverage.readthedocs.io/en/latest", packages=("coverage",), kind="sphinx"),
    "hypothesis": DocSite("https://hypothesis.readthedocs.io/en/latest", packages=("hypothesis",), kind="sphinx"),
    "mypy": DocSite("https://mypy.readthedocs.io/en/stable", packages=("mypy",), kind="sphinx"),
    "black": DocSite("https://black.readthedocs.io/en/stable", packages=("black",), kind="sphinx"),
    "tox": DocSite("https://tox.wiki/en/stable", packages=("tox",), kind="sphinx"),
    "watchdog": DocSite("https://python-watchdog.readthedocs.io/en/stable", packages=("watchdog",), kind="sphinx"),
    # CLI and terminal
    "click": DocSite("https://click.palletsprojects.com/en/stable", packages=("click",), kind="sphinx"),
    "rich": DocSite("https://rich.readthedocs.io/en/stable", packages=("rich",), kind="sphinx"),
    "tqdm": DocSite("https://tqdm.github.io", packages=("tqdm",), kind="sphinx"),
    "loguru": DocSite("https://loguru.readthedocs.io/en/stable", packages=("loguru",), kind="sphinx"),
    # Database and ORM
    "alembic": DocSite("https://alembic.sqlalchemy.org/en/latest", packages=("alembic",), kind="sphinx"),
    "psycopg": DocSite("https://www.psycopg.org/psycopg3/docs", ("psycopg3",), packages=("psycopg",), kind="sphinx"),
    "peewee": DocSite("https://docs.peewee-orm.com/en/latest", packages=("peewee",), kind="sphinx"),
    "tortoise-orm": DocSite("https://tortoise.github.io", packages=("tortoise",), kind="sphinx"),
    "redis-py": DocSite("https://redis.readthedocs.io/en/stable", packages=("redis",), kind="sphinx"),
    "motor": DocSite("https://motor.readthedocs.io/en/stable", packages=("motor",), kind="sphinx"),
    # Serialization and utilities
    "msgpack": DocSite("https://msgpack-python.readthedocs.io/en/stable", packages=("msgpack",), kind="sphinx"),
    "marshmallow": DocSite("https://marshmallow.readthedocs.io/en/stable", packages=("marshmallow",), kind="sphinx"),
    "attrs": DocSite("https://www.attrs.org/en/stable", packages=("attr", "attrs"), kind="sphinx"),
    "tenacity": DocSite("https://tenacity.readthedocs.io/en/latest", packages=("tenacity",), kind="sphinx"),
    "dateutil": DocSite("https://dateutil.readthedocs.io/en/stable", ("python-dateutil",), packages=("dateutil",), kind="sphinx"),
    "pendulum": DocSite("https://pendulum.eustace.io/docs", packages=("pendulum",), kind="sphinx"),
    "httpx": DocSite("https://www.python-httpx.org", kind="mkdocs", packages=("httpx",), fallbacks=("llms", "sitemap")),
    # Scraping and automation.
    "beautifulsoup4": DocSite("https://beautiful-soup-4.readthedocs.io/en/latest", ("bs4", "beautifulsoup", "bs"), packages=("bs4",), kind="sphinx"),
    "selenium": DocSite("https://www.selenium.dev/selenium/docs/api/py", packages=("selenium",), kind="sphinx"),
    # Discord forks (no packages= on pycord: it shares the `discord` package with discord.py).
    "pycord": DocSite("https://docs.pycord.dev/en/stable", ("py-cord",), kind="sphinx"),
    "nextcord": DocSite("https://docs.nextcord.dev/en/stable", packages=("nextcord",), kind="sphinx"),
    "disnake": DocSite("https://docs.disnake.dev/en/stable", packages=("disnake",), kind="sphinx"),
    # Machine learning and data (more).
    "pytorch": DocSite("https://pytorch.org/docs/stable", ("torch",), packages=("torch",), kind="sphinx"),
    "polars": DocSite("https://docs.pola.rs/api/python/stable", ("pl",), packages=("polars",), kind="sphinx"),
    "scikit-image": DocSite("https://scikit-image.org/docs/stable", ("skimage",), packages=("skimage",), kind="sphinx"),
    "joblib": DocSite("https://joblib.readthedocs.io/en/stable", packages=("joblib",), kind="sphinx"),
    "bokeh": DocSite("https://docs.bokeh.org/en/latest", packages=("bokeh",), kind="sphinx"),
    "nltk": DocSite("https://www.nltk.org", packages=("nltk",), kind="sphinx"),
    "shapely": DocSite("https://shapely.readthedocs.io/en/stable", packages=("shapely",), kind="sphinx"),
    "geopandas": DocSite("https://geopandas.org/en/stable", ("gpd",), packages=("geopandas",), kind="sphinx"),
    # Packaging and tooling.
    "sphinx": DocSite("https://www.sphinx-doc.org/en/master", packages=("sphinx",), kind="sphinx"),
    "pip": DocSite("https://pip.pypa.io/en/stable", kind="sphinx"),
    "setuptools": DocSite("https://setuptools.pypa.io/en/latest", ("setup",), packages=("setuptools", "pkg_resources"), kind="sphinx"),
    "packaging": DocSite("https://packaging.pypa.io/en/stable", packages=("packaging",), kind="sphinx"),
    "ipython": DocSite("https://ipython.readthedocs.io/en/stable", packages=("IPython",), kind="sphinx"),
    "ruff": DocSite("https://docs.astral.sh/ruff", kind="mkdocs", fallbacks=("llms", "sitemap")),
    "uv": DocSite("https://docs.astral.sh/uv", kind="mkdocs", fallbacks=("llms", "sitemap")),
    "mkdocs": DocSite("https://www.mkdocs.org", kind="mkdocs", fallbacks=("sitemap",)),
    # Async, web frameworks and servers.
    "celery": DocSite("https://docs.celeryq.dev/en/stable", packages=("celery",), kind="sphinx"),
    "aiosqlite": DocSite("https://aiosqlite.omnilib.dev/en/stable", packages=("aiosqlite",), kind="sphinx"),
    "starlette": DocSite("https://www.starlette.io", packages=("starlette",), kind="mkdocs", fallbacks=("llms", "sitemap")),
    "uvicorn": DocSite("https://www.uvicorn.org", packages=("uvicorn",), kind="mkdocs", fallbacks=("llms", "sitemap")),
    "typer": DocSite("https://typer.tiangolo.com", packages=("typer",), kind="mkdocs", fallbacks=("llms", "sitemap")),
    "sqlmodel": DocSite("https://sqlmodel.tiangolo.com", packages=("sqlmodel",), kind="mkdocs", fallbacks=("llms", "sitemap")),
    "textual": DocSite("https://textual.textualize.io", packages=("textual",), kind="mkdocs", fallbacks=("llms", "sitemap")),
    # Misc libraries.
    "docker-py": DocSite("https://docker-py.readthedocs.io/en/stable", ("docker",), packages=("docker",), kind="sphinx"),
    "typing-extensions": DocSite(
        "https://typing-extensions.readthedocs.io/en/latest", ("typing_extensions",), packages=("typing_extensions",), kind="sphinx"
    ),
    "jsonschema": DocSite("https://python-jsonschema.readthedocs.io/en/stable", packages=("jsonschema",), kind="sphinx"),
    "arrow": DocSite("https://arrow.readthedocs.io/en/stable", packages=("arrow",), kind="sphinx"),
    "prompt-toolkit": DocSite(
        "https://python-prompt-toolkit.readthedocs.io/en/stable", ("prompt_toolkit", "ptk"), packages=("prompt_toolkit",), kind="sphinx"
    ),
    "cachetools": DocSite("https://cachetools.readthedocs.io/en/stable", packages=("cachetools",), kind="sphinx"),
    "more-itertools": DocSite("https://more-itertools.readthedocs.io/en/stable", packages=("more_itertools",), kind="sphinx"),
    "sortedcontainers": DocSite("https://grantjenks.com/docs/sortedcontainers", packages=("sortedcontainers",), kind="sphinx"),
    "kivy": DocSite("https://kivy.org/doc/stable", packages=("kivy",), kind="sphinx"),
    # Web platform, from MDN's sitemap with per-page JSON for details.
    "html": DocSite("https://developer.mozilla.org/en-US/docs/Web/HTML", ("html5",), kind="mdn"),
    "css": DocSite("https://developer.mozilla.org/en-US/docs/Web/CSS", ("css3",), kind="mdn"),
    "js": DocSite("https://developer.mozilla.org/en-US/docs/Web/JavaScript", ("javascript", "ecmascript", "es"), kind="mdn"),
    "webapi": DocSite("https://developer.mozilla.org/en-US/docs/Web/API", ("dom", "api", "web"), kind="mdn"),
    "http": DocSite("https://developer.mozilla.org/en-US/docs/Web/HTTP", kind="mdn"),
    # More MDN.
    "svg": DocSite("https://developer.mozilla.org/en-US/docs/Web/SVG", kind="mdn"),
    "mathml": DocSite("https://developer.mozilla.org/en-US/docs/Web/MathML", kind="mdn"),
    "accessibility": DocSite("https://developer.mozilla.org/en-US/docs/Web/Accessibility", ("a11y",), kind="mdn"),
    "webassembly": DocSite("https://developer.mozilla.org/en-US/docs/WebAssembly", ("wasm",), kind="mdn"),
    "security": DocSite("https://developer.mozilla.org/en-US/docs/Web/Security", kind="mdn"),
    "performance": DocSite("https://developer.mozilla.org/en-US/docs/Web/Performance", ("perf",), kind="mdn"),
    "media": DocSite("https://developer.mozilla.org/en-US/docs/Web/Media", kind="mdn"),
    "webdriver": DocSite("https://developer.mozilla.org/en-US/docs/Web/WebDriver", kind="mdn"),
    "manifest": DocSite("https://developer.mozilla.org/en-US/docs/Web/Manifest", ("webmanifest",), kind="mdn"),
    "pwa": DocSite("https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps", kind="mdn"),
    "xpath": DocSite("https://developer.mozilla.org/en-US/docs/Web/XPath", kind="mdn"),
    "xslt": DocSite("https://developer.mozilla.org/en-US/docs/Web/XSLT", kind="mdn"),
    "webext": DocSite("https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions", ("webextensions",), kind="mdn"),
    # Frameworks and databases, rendered in chat through PAGE_SITES.
    "react": DocSite("https://react.dev", ("reactjs",), kind="llms"),
    "nextjs": DocSite("https://nextjs.org/docs", ("next",), kind="sitemap"),
    "vue": DocSite("https://vuejs.org", ("vuejs",), kind="llms"),
    "angular": DocSite("https://angular.dev", ("ng",), kind="llms"),
    "svelte": DocSite("https://svelte.dev", ("sveltekit",), kind="llms"),
    "mysql": DocSite("https://dev.mysql.com/doc/refman/8.4/en", kind="mysql"),
    "sqlite": DocSite("https://www.sqlite.org", ("sqlite3",), kind="sqlite"),
    "mongodb": DocSite("https://www.mongodb.com/docs/manual", kind="mongodb"),
    "redis": DocSite("https://redis.io/docs/latest", kind="sitemap"),
    # Web tools and CSS frameworks.
    "typescript": DocSite("https://www.typescriptlang.org/docs", ("ts",), kind="sitemap"),
    "tailwind": DocSite("https://tailwindcss.com/docs", ("tw", "tailwindcss"), kind="sitemap"),
    "bootstrap": DocSite("https://getbootstrap.com/docs", ("bs5",), kind="sitemap"),
    # Other languages and tools.
    "c": DocSite("https://en.cppreference.com/w/c", kind="cppreference"),
    "cpp": DocSite("https://en.cppreference.com/w/cpp", ("c++", "cxx"), kind="cppreference"),
    "rust": DocSite("https://doc.rust-lang.org/std", ("rs",), kind="rust"),
    "java": DocSite("https://docs.oracle.com/en/java/javase/21/docs/api", ("jdk", "javadoc"), kind="javadoc"),
    "sql": DocSite("https://www.postgresql.org/docs/current", ("postgres", "postgresql", "pg"), kind="postgres"),
    "nodejs": DocSite("https://nodejs.org/docs/latest/api", ("node",), kind="nodejs"),
    "go": DocSite("https://pkg.go.dev/std", ("golang",), kind="go"),
    "php": DocSite("https://www.php.net/manual/en", kind="php"),
    "git": DocSite("https://git-scm.com/docs", kind="git"),
    "haskell": DocSite("https://hoogle.haskell.org", ("hs", "hoogle"), kind="hoogle"),
}
