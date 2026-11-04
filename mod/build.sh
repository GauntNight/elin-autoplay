#!/usr/bin/env bash
# Build ElinBridge into mod/dist/ElinBridge. Every dotnet/NuGet cache stays inside the repo.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
root="$(cd "$here/.." && pwd -W 2>/dev/null || pwd)"
export DOTNET_CLI_HOME="$root/.cache/dotnet-home"
export NUGET_PACKAGES="$root/.cache/nuget/packages"
export NUGET_HTTP_CACHE_PATH="$root/.cache/nuget/http"
export NUGET_PLUGINS_CACHE_PATH="$root/.cache/nuget/plugins"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export MSBUILDDISABLENODEREUSE=1
dotnet build "$here/ElinBridge/ElinBridge.csproj" -c Release --disable-build-servers -nodeReuse:false \
  -p:RestoreConfigFile="$here/nuget.config" -v:minimal "$@"
ls -la "$here/dist/ElinBridge"
