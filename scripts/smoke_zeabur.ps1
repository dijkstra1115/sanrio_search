param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,
    [string]$Tag = "sanrio-search-local",
    [switch]$Headed
)

$resolvedImage = Resolve-Path $ImagePath
$imageFile = Split-Path -Leaf $resolvedImage
$imageDir = Split-Path -Parent $resolvedImage

docker build -t $Tag .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$dockerArgs = @(
    "run", "--rm",
    "-v", "${imageDir}:/input",
    $Tag,
    "python", "/app/app/scripts/smoke_lookup.py",
    "--image-path", "/input/$imageFile"
)

if ($Headed) {
    $dockerArgs += @("--headed", "--cli-command", "playwright-cli")
}

docker @dockerArgs
exit $LASTEXITCODE
