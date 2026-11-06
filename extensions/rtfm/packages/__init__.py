from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

from core.utils import NoticeLayout, truncate

from .cocoapods import CocoaPodsRegistry
from .conda import CondaRegistry
from .constants import MAX_VERSIONS, VERSIONS_PER_PAGE
from .crates import CratesRegistry
from .docker import DockerHubRegistry
from .ecosystem import (
    COCOAPODS,
    CONDA,
    CRATES,
    DOCKER,
    ECOSYSTEM_NAMES,
    GO,
    HEX,
    HOMEBREW,
    MAVEN,
    NPM,
    NUGET,
    PACKAGIST,
    PUB,
    PYPI,
    RUBYGEMS,
    SWIFT,
    Ecosystem,
    EcosystemConverter,
)
from .go import GoRegistry
from .hex import HexRegistry
from .homebrew import HomebrewRegistry
from .maven import MavenRegistry
from .npm import NpmRegistry
from .nuget import NuGetRegistry
from .pub import PubRegistry
from .pypi import PyPIRegistry
from .ruby import RubyGemsRegistry
from .swift import SwiftRegistry
from .utils import (
    Fetcher,
    PackageView,
    PackagistRegistry,
    Page,
    Registry,
    RegistryError,
    compare_items,
    dependency_items,
    info_items,
    search_items,
    versions_items,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from core import Bot

__all__ = ("Packages",)


class Packages(commands.Cog, name="Packages"):
    """Look up, compare and search packages across PyPI, npm, crates.io, Go, Packagist, RubyGems, NuGet, pub.dev, Hex.pm, Maven, Homebrew, Docker Hub, CocoaPods, Conda and Swift Package Index."""

    help_emoji = "\N{PACKAGE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        fetch = Fetcher(bot.http_session)
        self.registries: dict[Ecosystem, Registry] = {
            PYPI: PyPIRegistry(fetch),
            NPM: NpmRegistry(fetch),
            CRATES: CratesRegistry(fetch),
            GO: GoRegistry(fetch),
            PACKAGIST: PackagistRegistry(fetch),
            RUBYGEMS: RubyGemsRegistry(fetch),
            NUGET: NuGetRegistry(fetch),
            PUB: PubRegistry(fetch),
            HEX: HexRegistry(fetch),
            MAVEN: MavenRegistry(fetch),
            HOMEBREW: HomebrewRegistry(fetch),
            DOCKER: DockerHubRegistry(fetch),
            COCOAPODS: CocoaPodsRegistry(fetch),
            CONDA: CondaRegistry(fetch),
            SWIFT: SwiftRegistry(fetch),
        }

    async def deliver(self, ctx: commands.Context[Bot], producer: Awaitable[PackageView]) -> discord.Message:
        none = discord.AllowedMentions.none()

        async with ctx.typing():
            try:
                view = await producer
            except RegistryError as error:
                return await ctx.reply(view=NoticeLayout.error(str(error), title="Packages"), allowed_mentions=none)

        message = await ctx.reply(view=view, allowed_mentions=none)
        view.message = message
        return message

    @staticmethod
    def single(ctx: commands.Context[Bot], page: Page) -> PackageView:
        return PackageView(ctx.author, [page])

    async def info_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str) -> PackageView:
        registry = self.registries[eco]
        info = await registry.info(registry.validate(package))

        links: list[tuple[str, str]] = []
        if info.homepage and info.homepage != info.repository:
            links.append(("Homepage", info.homepage))
        if info.repository:
            links.append(("Repository", info.repository))
        if info.documentation and info.documentation != info.url:
            links.append(("Documentation", info.documentation))
        links.extend(info.extra_links)
        return self.single(ctx, Page(partial(info_items, info), url=info.url, label=f"Open on {eco.label}", colour=eco.colour, links=links))

    async def versions_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str) -> PackageView:
        registry = self.registries[eco]
        vlist = await registry.versions(registry.validate(package))
        if not vlist.entries:
            msg = f"`{vlist.name}` has no published versions."
            raise RegistryError(msg)

        vlist.entries = vlist.entries[:MAX_VERSIONS]
        pages = [
            Page(
                partial(versions_items, eco, vlist, vlist.entries[start : start + VERSIONS_PER_PAGE]),
                url=vlist.url,
                label=f"Open on {eco.label}",
                colour=eco.colour,
            )
            for start in range(0, len(vlist.entries), VERSIONS_PER_PAGE)
        ]
        return PackageView(ctx.author, pages)

    async def dependencies_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str, version: str | None) -> PackageView:
        registry = self.registries[eco]
        deps = await registry.dependencies(registry.validate(package), registry.validate_version(version))
        return self.single(ctx, Page(partial(dependency_items, eco, deps), url=deps.url, label=f"Open on {eco.label}", colour=eco.colour))

    @commands.group(name="pypisearch", aliases=["pypi"], invoke_without_command=True, extras={"examples": ["pypisearch requests"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypisearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a Python package directly from PyPI."""
        return await self.deliver(ctx, self.info_view(ctx, PYPI, package))

    @pypisearch.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["pypisearch versions requests"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Python package, newest first."""
        return await self.deliver(ctx, self.versions_view(ctx, PYPI, package))

    @pypisearch.command(
        name="dependencies",
        aliases=["dependency", "deps", "requires"],
        extras={"examples": ["pypisearch dependencies requests", "pypisearch deps requests 2.31.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies a Python package declares, including optional extras."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PYPI, package, version))

    @pypisearch.command(name="search", aliases=["find", "s"], extras={"examples": ["pypisearch search async http"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on PyPI."),
    ) -> discord.Message:
        """Searches PyPI for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PYPI, query))

    @commands.group(name="npmsearch", aliases=["npm"], invoke_without_command=True, extras={"examples": ["npmsearch react", "npmsearch @types/node"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npmsearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about an npm package directly from the npm Registry."""
        return await self.deliver(ctx, self.info_view(ctx, NPM, package))

    @npmsearch.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["npmsearch versions react"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of an npm package, newest first, with their dist-tags."""
        return await self.deliver(ctx, self.versions_view(ctx, NPM, package))

    @npmsearch.command(
        name="deps",
        aliases=["dependencies", "dependency"],
        extras={"examples": ["npmsearch deps express", "npmsearch deps express 4.18.2"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version or dist-tag. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies, peer dependencies and dev dependencies of an npm package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, NPM, package, version))

    @npmsearch.command(name="search", aliases=["find", "s"], extras={"examples": ["npmsearch search state management"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on npm."),
    ) -> discord.Message:
        """Searches npm for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, NPM, query))

    @commands.group(name="crate", aliases=["crates"], invoke_without_command=True, extras={"examples": ["crate serde"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate to search for."),
    ) -> discord.Message:
        """Get info about a Rust crate directly from crates.io."""
        return await self.deliver(ctx, self.info_view(ctx, CRATES, package))

    @crate.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["crate versions serde"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate whose published versions to list."),
    ) -> discord.Message:
        """Shows the published versions of a Rust crate, including yanked ones."""
        return await self.deliver(ctx, self.versions_view(ctx, CRATES, package))

    @crate.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["crate deps serde", "crate deps serde 1.0.200"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable one."),
    ) -> discord.Message:
        """Shows the normal, optional, build and dev dependencies of a Rust crate."""
        return await self.deliver(ctx, self.dependencies_view(ctx, CRATES, package, version))

    @crate.command(name="search", aliases=["find", "s"], extras={"examples": ["crate search async runtime"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on crates.io."),
    ) -> discord.Message:
        """Searches crates.io for Rust crates matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, CRATES, query))

    @commands.group(
        name="gosearch",
        aliases=["gopkg", "gomod"],
        invoke_without_command=True,
        extras={"examples": ["gosearch github.com/gin-gonic/gin", "gosearch cobra"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gosearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module path or package keyword."),
    ) -> discord.Message:
        """Get info about a Go module or package from pkg.go.dev and the Go Module Proxy."""
        return await self.deliver(ctx, self.info_view(ctx, GO, package))

    @gosearch.command(
        name="versions", aliases=["version", "releases", "history"], extras={"examples": ["gosearch versions github.com/gin-gonic/gin"]}
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Go module, newest first."""
        return await self.deliver(ctx, self.versions_view(ctx, GO, package))

    @gosearch.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["gosearch deps github.com/gin-gonic/gin", "gosearch deps github.com/spf13/cobra 1.8.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module whose go.mod dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the direct and indirect module requirements declared in a Go module's go.mod."""
        return await self.deliver(ctx, self.dependencies_view(ctx, GO, package, version))

    @gosearch.command(name="search", aliases=["find", "s"], extras={"examples": ["gosearch search websocket"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on pkg.go.dev."),
    ) -> discord.Message:
        """Searches pkg.go.dev for Go packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, GO, query))

    @commands.group(
        name="packagist",
        aliases=["composer", "phpsearch", "phppkg"],
        invoke_without_command=True,
        extras={"examples": ["packagist laravel/framework", "packagist monolog"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Composer package (`vendor/package` or name)."),
    ) -> discord.Message:
        """Get info about a PHP Composer package from Packagist."""
        return await self.deliver(ctx, self.info_view(ctx, PACKAGIST, package))

    @packagist.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["packagist versions monolog/monolog"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The PHP package whose published versions to list."),
    ) -> discord.Message:
        """Lists the tagged releases of a PHP Composer package on Packagist."""
        return await self.deliver(ctx, self.versions_view(ctx, PACKAGIST, package))

    @packagist.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["packagist deps guzzlehttp/guzzle", "packagist deps monolog/monolog 3.7.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The PHP package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable release."),
    ) -> discord.Message:
        """Shows the required packages, PHP extensions, dev dependencies and suggestions of a Composer package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PACKAGIST, package, version))

    @packagist.command(name="search", aliases=["find", "s"], extras={"examples": ["packagist search http client"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Packagist."),
    ) -> discord.Message:
        """Searches Packagist for PHP Composer packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PACKAGIST, query))

    @commands.group(name="gem", aliases=["rubygems", "gemsearch"], invoke_without_command=True, extras={"examples": ["gem rails", "gem nokogiri"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Ruby gem to look up."),
    ) -> discord.Message:
        """Get info about a Ruby gem from RubyGems.org."""
        return await self.deliver(ctx, self.info_view(ctx, RUBYGEMS, package))

    @gem.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["gem versions rails"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The gem whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Ruby gem."""
        return await self.deliver(ctx, self.versions_view(ctx, RUBYGEMS, package))

    @gem.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["gem deps rails", "gem deps sinatra 4.0.0"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The gem whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the runtime and development dependencies of a Ruby gem."""
        return await self.deliver(ctx, self.dependencies_view(ctx, RUBYGEMS, package, version))

    @gem.command(name="search", aliases=["find", "s"], extras={"examples": ["gem search markdown parser"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on RubyGems."),
    ) -> discord.Message:
        """Searches RubyGems.org for gems matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, RUBYGEMS, query))

    @commands.group(
        name="nuget",
        aliases=["dotnet", "nugetsearch"],
        invoke_without_command=True,
        extras={"examples": ["nuget Newtonsoft.Json", "nuget Serilog"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package ID to look up."),
    ) -> discord.Message:
        """Get info about a .NET package from NuGet.org."""
        return await self.deliver(ctx, self.info_view(ctx, NUGET, package))

    @nuget.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["nuget versions Newtonsoft.Json"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a NuGet package."""
        return await self.deliver(ctx, self.versions_view(ctx, NUGET, package))

    @nuget.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["nuget deps Serilog"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the target-framework dependency groups of a NuGet package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, NUGET, package, version))

    @nuget.command(name="search", aliases=["find", "s"], extras={"examples": ["nuget search json serializer"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on NuGet."),
    ) -> discord.Message:
        """Searches NuGet.org for .NET packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, NUGET, query))

    @commands.group(
        name="pub",
        aliases=["pubdev", "pubsearch", "flutter"],
        invoke_without_command=True,
        extras={"examples": ["pub dio", "pub provider"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Dart or Flutter package to look up."),
    ) -> discord.Message:
        """Get info about a Dart or Flutter package from pub.dev."""
        return await self.deliver(ctx, self.info_view(ctx, PUB, package))

    @pub.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["pub versions dio"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The pub.dev package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Dart or Flutter package."""
        return await self.deliver(ctx, self.versions_view(ctx, PUB, package))

    @pub.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["pub deps dio"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The pub.dev package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies and dev dependencies of a Dart or Flutter package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PUB, package, version))

    @pub.command(name="search", aliases=["find", "s"], extras={"examples": ["pub search state management"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on pub.dev."),
    ) -> discord.Message:
        """Searches pub.dev for Dart and Flutter packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PUB, query))

    @commands.group(
        name="hex",
        aliases=["hexpm", "hexsearch"],
        invoke_without_command=True,
        extras={"examples": ["hex phoenix", "hex ecto"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_command(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Elixir or Erlang package to look up."),
    ) -> discord.Message:
        """Get info about an Elixir, Erlang or Gleam package from Hex.pm."""
        return await self.deliver(ctx, self.info_view(ctx, HEX, package))

    @hex_command.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["hex versions phoenix"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Hex package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Hex.pm package."""
        return await self.deliver(ctx, self.versions_view(ctx, HEX, package))

    @hex_command.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["hex deps phoenix"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Hex package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable one."),
    ) -> discord.Message:
        """Shows the dependencies of a Hex.pm package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, HEX, package, version))

    @hex_command.command(name="search", aliases=["find", "s"], extras={"examples": ["hex search graphql"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Hex.pm."),
    ) -> discord.Message:
        """Searches Hex.pm for Elixir and Erlang packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, HEX, query))

    @commands.group(
        name="maven",
        aliases=["mvn", "gradle", "mavensearch"],
        invoke_without_command=True,
        extras={"examples": ["maven com.google.guava:guava", "maven gson"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def maven(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Maven artifact (`groupId:artifactId` or artifact name)."),
    ) -> discord.Message:
        """Get info about a Java/JVM artifact from Maven Central."""
        return await self.deliver(ctx, self.info_view(ctx, MAVEN, package))

    @maven.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["maven versions com.google.guava:guava"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def maven_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Maven artifact whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of an artifact on Maven Central."""
        return await self.deliver(ctx, self.versions_view(ctx, MAVEN, package))

    @maven.command(
        name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["maven deps com.fasterxml.jackson.core:jackson-databind"]}
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def maven_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Maven artifact whose POM dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the compile, runtime, test and optional dependencies declared in an artifact's POM."""
        return await self.deliver(ctx, self.dependencies_view(ctx, MAVEN, package, version))

    @maven.command(name="search", aliases=["find", "s"], extras={"examples": ["maven search slf4j"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def maven_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Maven Central."),
    ) -> discord.Message:
        """Searches Maven Central for JVM artifacts matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, MAVEN, query))

    @commands.group(
        name="brew",
        aliases=["homebrew", "brewsearch"],
        invoke_without_command=True,
        extras={"examples": ["brew wget", "brew ffmpeg"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def brew(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Homebrew formula to look up."),
    ) -> discord.Message:
        """Get info about a Homebrew formula from formulae.brew.sh."""
        return await self.deliver(ctx, self.info_view(ctx, HOMEBREW, package))

    @brew.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["brew versions python@3.12"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def brew_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Homebrew formula whose versions to list."),
    ) -> discord.Message:
        """Lists the stable, HEAD and versioned formulae of a Homebrew package."""
        return await self.deliver(ctx, self.versions_view(ctx, HOMEBREW, package))

    @brew.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["brew deps ffmpeg"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def brew_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Homebrew formula whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="Optional version."),
    ) -> discord.Message:
        """Shows the runtime, build, test and optional dependencies of a Homebrew formula."""
        return await self.deliver(ctx, self.dependencies_view(ctx, HOMEBREW, package, version))

    @brew.command(name="search", aliases=["find", "s"], extras={"examples": ["brew search http benchmark"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def brew_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Homebrew."),
    ) -> discord.Message:
        """Searches Homebrew formulae matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, HOMEBREW, query))

    @commands.group(
        name="docker",
        aliases=["dockerhub", "container"],
        invoke_without_command=True,
        extras={"examples": ["docker nginx", "docker bitnami/redis"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def docker(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Docker Hub repository (`image` or `namespace/image`)."),
    ) -> discord.Message:
        """Get info about a container image repository from Docker Hub."""
        return await self.deliver(ctx, self.info_view(ctx, DOCKER, package))

    @docker.command(name="versions", aliases=["version", "tags", "releases", "history"], extras={"examples": ["docker versions postgres"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def docker_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Docker Hub image whose published tags to list."),
    ) -> discord.Message:
        """Lists the published image tags and sizes on Docker Hub."""
        return await self.deliver(ctx, self.versions_view(ctx, DOCKER, package))

    @docker.command(
        name="deps", aliases=["dependencies", "arches", "images"], extras={"examples": ["docker deps alpine", "docker deps python 3.12-slim"]}
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def docker_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Docker Hub repository whose platform images to show."),
        version: str | None = commands.parameter(default=None, description="A specific tag. Defaults to `latest`."),
    ) -> discord.Message:
        """Shows the OS/architecture image variants and digests for a Docker Hub tag."""
        return await self.deliver(ctx, self.dependencies_view(ctx, DOCKER, package, version))

    @docker.command(name="search", aliases=["find", "s"], extras={"examples": ["docker search reverse proxy"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def docker_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Docker Hub."),
    ) -> discord.Message:
        """Searches Docker Hub for container images matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, DOCKER, query))

    @commands.group(
        name="pod",
        aliases=["cocoapods", "pods", "podsearch"],
        invoke_without_command=True,
        extras={"examples": ["pod Alamofire", "pod SnapKit"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pod(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The CocoaPods pod name to look up."),
    ) -> discord.Message:
        """Get info about an iOS/macOS CocoaPod from CocoaPods.org."""
        return await self.deliver(ctx, self.info_view(ctx, COCOAPODS, package))

    @pod.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["pod versions Alamofire"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pod_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The CocoaPod whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a CocoaPod."""
        return await self.deliver(ctx, self.versions_view(ctx, COCOAPODS, package))

    @pod.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["pod deps Moya"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pod_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The CocoaPod whose dependencies and subspecs to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the pod dependencies, subspecs and system frameworks of a CocoaPod."""
        return await self.deliver(ctx, self.dependencies_view(ctx, COCOAPODS, package, version))

    @pod.command(name="search", aliases=["find", "s"], extras={"examples": ["pod search networking"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pod_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on CocoaPods."),
    ) -> discord.Message:
        """Searches CocoaPods.org for pods matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, COCOAPODS, query))

    @commands.group(
        name="conda",
        aliases=["anaconda", "condaforge", "mamba"],
        invoke_without_command=True,
        extras={"examples": ["conda numpy", "conda conda-forge/scipy"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def conda(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Conda package (`package` or `channel/package`)."),
    ) -> discord.Message:
        """Get info about a Conda package from Anaconda.org (defaults to conda-forge)."""
        return await self.deliver(ctx, self.info_view(ctx, CONDA, package))

    @conda.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["conda versions numpy"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def conda_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Conda package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions and build counts of a Conda package."""
        return await self.deliver(ctx, self.versions_view(ctx, CONDA, package))

    @conda.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["conda deps pandas"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def conda_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Conda package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the platform subdir dependencies of a Conda package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, CONDA, package, version))

    @conda.command(name="search", aliases=["find", "s"], extras={"examples": ["conda search bioinformatics"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def conda_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Anaconda.org."),
    ) -> discord.Message:
        """Searches Anaconda.org channels for Conda packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, CONDA, query))

    @commands.group(
        name="swift",
        aliases=["spm", "swiftpm", "spi"],
        invoke_without_command=True,
        extras={"examples": ["swift apple/swift-nio", "swift Alamofire/Alamofire"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def swift(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Swift package (`owner/repo` or package name)."),
    ) -> discord.Message:
        """Get info about a Swift package from the Swift Package Index and GitHub."""
        return await self.deliver(ctx, self.info_view(ctx, SWIFT, package))

    @swift.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["swift versions apple/swift-nio"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def swift_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Swift package whose tagged releases to list."),
    ) -> discord.Message:
        """Lists the tagged releases and versions of a Swift package."""
        return await self.deliver(ctx, self.versions_view(ctx, SWIFT, package))

    @swift.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["swift deps vapor/vapor"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def swift_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Swift package whose Package.swift dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version tag. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the package dependencies and platform targets declared in Package.swift."""
        return await self.deliver(ctx, self.dependencies_view(ctx, SWIFT, package, version))

    @swift.command(name="search", aliases=["find", "s"], extras={"examples": ["swift search argument parser"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def swift_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on the Swift Package Index."),
    ) -> discord.Message:
        """Searches the Swift Package Index for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, SWIFT, query))

    @commands.group(name="package", aliases=["pkg"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Look up, compare and search packages across PyPI, npm, crates.io, Go, Packagist, RubyGems, NuGet, pub.dev, Hex.pm, Maven, Homebrew, Docker Hub, CocoaPods, Conda and Swift Package Index."""
        return await ctx.send_help(ctx.command)

    @package.command(
        name="info",
        aliases=["show", "i"],
        extras={"examples": ["package info go github.com/gin-gonic/gin", "package info maven com.google.guava:guava", "package info brew ffmpeg"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_info(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package name."),
    ) -> discord.Message:
        """Shows detailed metadata for a package in any supported ecosystem."""
        return await self.deliver(ctx, self.info_view(ctx, ecosystem, package))

    @package.command(
        name="versions",
        aliases=["version", "releases", "history"],
        extras={"examples": ["package versions go github.com/spf13/cobra", "package versions docker postgres"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_versions(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package whose versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a package in any supported ecosystem."""
        return await self.deliver(ctx, self.versions_view(ctx, ecosystem, package))

    @package.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["package deps go github.com/gin-gonic/gin", "package deps maven com.google.guava:guava"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_dependencies(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the declared dependencies of a package in any supported ecosystem."""
        return await self.deliver(ctx, self.dependencies_view(ctx, ecosystem, package, version))

    @package.command(
        name="compare",
        aliases=["vs", "diff"],
        extras={
            "examples": [
                "package compare pypi requests httpx",
                "package compare brew wget curl",
                "package compare docker nginx caddy",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_compare(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the packages live: {ECOSYSTEM_NAMES}.",
        ),
        first: str = commands.parameter(description="The first package."),
        second: str = commands.parameter(description="The second package."),
    ) -> discord.Message:
        """Compares the metadata of two packages from the same ecosystem side by side."""
        return await self.deliver(ctx, self.compare_view(ctx, ecosystem, first, second))

    async def compare_view(self, ctx: commands.Context[Bot], eco: Ecosystem, first: str, second: str) -> PackageView:
        registry = self.registries[eco]
        first, second = registry.validate(first), registry.validate(second)
        if first.casefold() == second.casefold():
            msg = "Pick two different packages to compare."
            raise RegistryError(msg)

        left, right = await asyncio.gather(registry.info(first), registry.info(second))
        return self.single(
            ctx,
            Page(
                partial(compare_items, left, right),
                url=left.url,
                label=truncate(f"Open {left.name}", 80),
                colour=eco.colour,
                links=[(truncate(f"Open {right.name}", 80), right.url)],
            ),
        )

    @package.command(
        name="search",
        aliases=["find", "s"],
        extras={
            "examples": [
                "package search pypi http client",
                "package search maven json",
                "package search brew benchmark",
                "package search docker postgres",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_search(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where to search: {ECOSYSTEM_NAMES}.",
        ),
        *,
        query: str = commands.parameter(description="What to look for."),
    ) -> discord.Message:
        """Searches a package registry for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, ecosystem, query))

    async def search_view(self, ctx: commands.Context[Bot], eco: Ecosystem, query: str) -> PackageView:
        query = " ".join(query.split())
        if not query or len(query) > 100:
            msg = "The search query must be between 1 and 100 characters."
            raise RegistryError(msg)

        result = await self.registries[eco].search(query)
        return self.single(ctx, Page(partial(search_items, eco, query, result), url=None, colour=eco.colour))
