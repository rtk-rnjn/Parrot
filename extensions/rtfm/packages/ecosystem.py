from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot


@dataclass(frozen=True, slots=True, eq=False)
class Ecosystem:
    key: str
    label: str
    colour: discord.Colour
    icon: str
    install: str
    requires_label: str
    name_pattern: re.Pattern[str]
    aliases: tuple[str, ...]
    page: str

    def page_url(self, name: str) -> str:
        return self.page.format(name=quote(name, safe="@/:"))


PYPI = Ecosystem(
    key="pypi",
    label="PyPI",
    colour=discord.Colour.teal(),
    icon="https://i.imgur.com/syDydkb.png",
    install="pip install {name}",
    requires_label="Python",
    name_pattern=re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?"),
    aliases=("pypi", "pip", "py", "python"),
    page="https://pypi.org/project/{name}/",
)
NPM = Ecosystem(
    key="npm",
    label="npm",
    colour=discord.Colour(0xCC3534),
    icon="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png",
    install="npm install {name}",
    requires_label="Node.js",
    name_pattern=re.compile(r"(?:@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*", re.IGNORECASE),
    aliases=("npm", "node", "nodejs", "js", "javascript"),
    page="https://www.npmjs.com/package/{name}",
)
CRATES = Ecosystem(
    key="crates",
    label="crates.io",
    colour=discord.Colour(0xE03D29),
    icon="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/2048px-Rust_programming_language_black_logo.svg.png",
    install="cargo add {name}",
    requires_label="Rust",
    name_pattern=re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}"),
    aliases=("crates", "crate", "cargo", "rust", "rs"),
    page="https://crates.io/crates/{name}",
)
GO = Ecosystem(
    key="go",
    label="pkg.go.dev",
    colour=discord.Colour(0x00ADD8),
    icon="https://go.dev/blog/go-brand/Go-Logo/PNG/Go-Logo_Blue.png",
    install="go get {name}",
    requires_label="Go",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._~/-]{0,127}"),
    aliases=("go", "golang", "godev", "gomod", "gopkg"),
    page="https://pkg.go.dev/{name}",
)
PACKAGIST = Ecosystem(
    key="packagist",
    label="Packagist",
    colour=discord.Colour(0xF28D1A),
    icon="https://packagist.org/img/logo-small.png",
    install="composer require {name}",
    requires_label="PHP",
    name_pattern=re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?(?:/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)?"),
    aliases=("packagist", "composer", "php"),
    page="https://packagist.org/packages/{name}",
)
RUBYGEMS = Ecosystem(
    key="rubygems",
    label="RubyGems",
    colour=discord.Colour(0xE9573F),
    icon="https://rubygems.org/favicon.ico",
    install="gem install {name}",
    requires_label="Ruby",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"),
    aliases=("rubygems", "gem", "gems", "ruby", "rb"),
    page="https://rubygems.org/gems/{name}",
)
NUGET = Ecosystem(
    key="nuget",
    label="NuGet",
    colour=discord.Colour(0x004880),
    icon="https://www.nuget.org/Content/gallery/img/logo-og-600x600.png",
    install="dotnet add package {name}",
    requires_label=".NET",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"),
    aliases=("nuget", "dotnet", "csharp", "cs", "net"),
    page="https://www.nuget.org/packages/{name}",
)
PUB = Ecosystem(
    key="pub",
    label="pub.dev",
    colour=discord.Colour(0x0175C2),
    icon="https://pub.dev/static/hash-6pt3begn/img/pub-dev-icon-cover-image.png",
    install="dart pub add {name}",
    requires_label="Dart SDK",
    name_pattern=re.compile(r"[a-zA-Z0-9_]{1,64}"),
    aliases=("pub", "pubdev", "dart", "flutter"),
    page="https://pub.dev/packages/{name}",
)
HEX = Ecosystem(
    key="hex",
    label="Hex.pm",
    colour=discord.Colour(0x6E4A7E),
    icon="https://hex.pm/images/hex.png",
    install='{{:{name}, "~> {version}"}}',
    requires_label="Elixir",
    name_pattern=re.compile(r"[a-zA-Z0-9_]{1,64}"),
    aliases=("hex", "hexpm", "elixir", "ex", "erlang", "gleam"),
    page="https://hex.pm/packages/{name}",
)
MAVEN = Ecosystem(
    key="maven",
    label="Maven Central",
    colour=discord.Colour(0xC71A36),
    icon="https://maven.apache.org/images/maven-logo-black-on-white.png",
    install='implementation("{name}:{version}")',
    requires_label="Java / JVM",
    name_pattern=re.compile(r"[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)?"),
    aliases=("maven", "mvn", "gradle", "java", "kotlin", "jvm"),
    page="https://central.sonatype.com/artifact/{name}",
)
HOMEBREW = Ecosystem(
    key="homebrew",
    label="Homebrew",
    colour=discord.Colour(0xFBB040),
    icon="https://brew.sh/assets/img/homebrew.svg",
    install="brew install {name}",
    requires_label="OS / macOS",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,99}"),
    aliases=("homebrew", "brew", "macos"),
    page="https://formulae.brew.sh/formula/{name}",
)
DOCKER = Ecosystem(
    key="docker",
    label="Docker Hub",
    colour=discord.Colour(0x2496ED),
    icon="https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png",
    install="docker pull {name}:{version}",
    requires_label="Architectures",
    name_pattern=re.compile(r"(?:[a-z0-9_.-]+/)?[a-z0-9_.-]+", re.IGNORECASE),
    aliases=("docker", "dockerhub", "container", "oci"),
    page="https://hub.docker.com/r/{name}",
)
COCOAPODS = Ecosystem(
    key="cocoapods",
    label="CocoaPods",
    colour=discord.Colour(0xEE3322),
    icon="https://cocoapods.org/favicons/apple-touch-icon.png",
    install="pod '{name}', '~> {version}'",
    requires_label="Platforms",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,99}"),
    aliases=("cocoapods", "pod", "pods", "ios"),
    page="https://cocoapods.org/pods/{name}",
)
CONDA = Ecosystem(
    key="conda",
    label="Conda",
    colour=discord.Colour(0x44A833),
    icon="https://conda.io/en/latest/_images/conda_logo.svg",
    install="conda install -c {name}",
    requires_label="Subdirs / Python",
    name_pattern=re.compile(r"(?:[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+"),
    aliases=("conda", "anaconda", "conda-forge", "condaforge", "mamba"),
    page="https://anaconda.org/{name}",
)
SWIFT = Ecosystem(
    key="swift",
    label="Swift Package Index",
    colour=discord.Colour(0xF05138),
    icon="https://swiftpackageindex.com/images/logo.svg",
    install='.package(url: "https://github.com/{name}.git", from: "{version}")',
    requires_label="Swift / Platforms",
    name_pattern=re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?"),
    aliases=("swift", "spm", "swiftpm", "spi"),
    page="https://swiftpackageindex.com/{name}",
)

ECOSYSTEMS = (
    PYPI,
    NPM,
    CRATES,
    GO,
    PACKAGIST,
    RUBYGEMS,
    NUGET,
    PUB,
    HEX,
    MAVEN,
    HOMEBREW,
    DOCKER,
    COCOAPODS,
    CONDA,
    SWIFT,
)
ECOSYSTEM_NAMES = ", ".join(f"`{eco.key}`" for eco in ECOSYSTEMS)


class EcosystemConverter(commands.Converter[Ecosystem]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> Ecosystem:
        wanted = argument.strip().casefold()
        for ecosystem in ECOSYSTEMS:
            if wanted == ecosystem.label.casefold() or wanted in ecosystem.aliases:
                return ecosystem
        msg = f"The ecosystem should be one of: {ECOSYSTEM_NAMES}."
        raise commands.BadArgument(msg)
