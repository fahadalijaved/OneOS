# Launch in its own PowerShell 7 process. The only token input is the masked box.
param([switch]$CheckLocalSetup)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$base = Join-Path $root 'out/github-packages-access'
$seedPath = Join-Path $PSScriptRoot 'oneos-package-seeds.json'
$seedSha = '0529a6c38544dc958a265de1e4f7f0e98c183e0cc27fbd62ff76090daaaa6b1c'
$script:stage = 'local setup'
$script:httpStatus = 0
$script:total = 0L
$script:client = $null
$script:packageAuth = $null
$script:current = ''
$handler = $null
$form = $null
$field = $null
$token = $null
$username = $null
$run = $null
$files = [Collections.Generic.List[object]]::new()
$coordinates = [Collections.Generic.List[object]]::new()
$registries = @{
    'sesl-androidx' = 'https://maven.pkg.github.com/tribalfs/sesl-androidx'
    'sesl-material-components-android' = 'https://maven.pkg.github.com/tribalfs/sesl-material-components-android'
    'oneui-design' = 'https://maven.pkg.github.com/tribalfs/oneui-design'
}
$strictPins = @{}
$pending = [Collections.Generic.Queue[object]]::new()
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

function Get-Registry([string]$Group, [string]$Artifact) {
    if ($Group.StartsWith('sesl.androidx.', [StringComparison]::Ordinal)) { return 'sesl-androidx' }
    if ($Group -ceq 'sesl.com.google.android.material' -and $Artifact -ceq 'material') {
        return 'sesl-material-components-android'
    }
    if ($Group -ceq 'io.github.tribalfs' -and $Artifact -ceq 'oneui-design') { return 'oneui-design' }
    return $null
}

function Add-Coordinate([string]$Group, [string]$Artifact, [string]$Version) {
    $registry = Get-Registry $Group $Artifact
    if (!$registry) { return }
    if ($Group -cnotmatch '^[a-z0-9]+(?:\.[a-z0-9]+)*$' -or
        $Artifact -cnotmatch '^[a-z0-9][a-z0-9_.-]{0,127}$') { throw 'Invalid coordinate' }
    $key = "${Group}:${Artifact}"
    if ($strictPins.ContainsKey($key)) { $Version = $strictPins[$key] }
    if ($Version -cnotmatch '^[0-9][A-Za-z0-9._+-]{0,95}$' -or $Version.EndsWith('+') -or
        $Version.EndsWith('.') -or $Version -match '(?i)snapshot$') { throw 'Nonliteral private version' }
    if (!$seen.Add("${key}:${Version}")) { return }
    if ($seen.Count -gt 96) { throw 'Private graph limit' }
    $pending.Enqueue(@{ group = $Group; artifact = $Artifact; version = $Version; registry = $registry })
}

function Read-PackageBytes([string]$Url, [Net.Http.Headers.AuthenticationHeaderValue]$Auth,
        [int]$Limit, [switch]$Optional, [switch]$CheckScope) {
    $script:httpStatus = 0
    $request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Get, $Url)
    $response = $null
    $stream = $null
    $body = $null
    $deadline = [Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(45))
    try {
        $request.Headers.Authorization = $Auth
        $response = $script:client.Send($request, [Net.Http.HttpCompletionOption]::ResponseHeadersRead, $deadline.Token)
        $script:httpStatus = [int]$response.StatusCode
        if ($Optional -and $script:httpStatus -eq 404) { return $null }
        if ($script:httpStatus -eq 302 -and !$CheckScope -and $null -ne $Auth -and
            $Auth.Scheme -ceq 'Basic' -and $request.RequestUri.Scheme -ceq 'https' -and
            $request.RequestUri.Port -eq 443 -and !$request.RequestUri.UserInfo -and
            $request.RequestUri.IdnHost -ceq 'maven.pkg.github.com') {
            $location = $response.Headers.Location
            if ($null -eq $location -or !$location.IsAbsoluteUri -or
                $location.Scheme -cne 'https' -or $location.Port -ne 443 -or
                $location.UserInfo -or $location.Fragment -or $location.OriginalString.Length -gt 8192 -or
                $location.IdnHost -cnotin @('mavenregistryv2prod.blob.core.windows.net',
                    'pkg-containers.githubusercontent.com', 'github-registry-files.githubusercontent.com')) {
                throw 'Package download redirect refused'
            }
            # The signed location is itself access material. Do not log it,
            # copy its query into receipts, or forward registry credentials.
            $response.Dispose()
            $response = $null
            $request.Headers.Authorization = $null
            $request.Dispose()
            $request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Get, $location)
            $response = $script:client.Send($request,
                [Net.Http.HttpCompletionOption]::ResponseHeadersRead, $deadline.Token)
            $script:httpStatus = [int]$response.StatusCode
        }
        if ($script:httpStatus -ne 200) { throw 'Unexpected HTTP status' }
        if ($CheckScope) {
            $script:stage = 'GitHub token scope header'
            if (!$response.Headers.Contains('X-OAuth-Scopes')) { throw 'Missing scope header' }
            $scopeText = $response.Headers.GetValues('X-OAuth-Scopes') -join ','
            $scopes = @($scopeText -split ',' |
                ForEach-Object { $_.Trim() } | Where-Object { $_ })
            if ($scopes -cnotcontains 'read:packages') {
                $script:stage = 'token missing read:packages'
                throw 'Missing required package scope'
            }
            if ($scopes.Count -ne 1) {
                $script:stage = 'token has scopes beyond read:packages'
                throw 'Unexpected extra scopes'
            }
            $script:stage = 'GitHub identity response body'
        }
        if ($null -ne $response.Content.Headers.ContentLength -and
            $response.Content.Headers.ContentLength -gt $Limit) { throw 'Response length limit' }
        $stream = $response.Content.ReadAsStream($deadline.Token)
        $body = [IO.MemoryStream]::new()
        $buffer = [byte[]]::new(65536)
        while (($read = $stream.ReadAsync($buffer, 0, $buffer.Length, $deadline.Token).GetAwaiter().GetResult()) -ne 0) {
            if ($body.Length + $read -gt $Limit) { throw 'Response byte limit' }
            $body.Write($buffer, 0, $read)
        }
        return ,$body.ToArray()
    } finally {
        $request.Headers.Authorization = $null
        if ($null -ne $body) { $body.Dispose() }
        if ($null -ne $stream) { $stream.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
        $request.Dispose()
        $deadline.Dispose()
    }
}

function Save-Library([hashtable]$Coordinate, [string]$Name, [byte[]]$Bytes) {
    $script:total += $Bytes.Length
    if ($script:total -gt 512MB -or $files.Count -ge 384) { throw 'Mirror size limit' }
    $prefix = $Coordinate.group.Replace('.', '/') + '/' + $Coordinate.artifact + '/' + $Coordinate.version
    $relative = "$prefix/$Name"
    $path = Join-Path $run "maven/$relative"
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)) | Out-Null
    $output = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $output.Write($Bytes, 0, $Bytes.Length) } finally { $output.Dispose() }
    $files.Add(@{ path = $relative; bytes = $Bytes.Length; registry = $Coordinate.registry
        sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant() })
}

function Get-MavenValue($Node, [string]$Element, $Ns) {
    $item = $Node.SelectSingleNode("m:$Element", $Ns)
    if ($null -ne $item) { return $item.InnerText.Trim() }
    return ''
}

function Read-Pom([byte[]]$Bytes, [hashtable]$Coordinate) {
    $settings = [Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $settings.MaxCharactersInDocument = 2MB
    $inputStream = [IO.MemoryStream]::new($Bytes)
    try {
        $reader = [Xml.XmlReader]::Create($inputStream, $settings)
        try {
            $pom = [Xml.XmlDocument]::new()
            $pom.XmlResolver = $null
            $pom.Load($reader)
        } finally { $reader.Dispose() }
    } finally { $inputStream.Dispose() }
    $ns = [Xml.XmlNamespaceManager]::new($pom.NameTable)
    $ns.AddNamespace('m', 'http://maven.apache.org/POM/4.0.0')
    $project = $pom.SelectSingleNode('/m:project', $ns)
    if ($null -eq $project -or (Get-MavenValue $project 'artifactId' $ns) -cne $Coordinate.artifact) {
        throw 'POM identity mismatch'
    }
    $parent = $project.SelectSingleNode('m:parent', $ns)
    foreach ($item in @(@{ tag = 'groupId'; value = $Coordinate.group }, @{ tag = 'version'; value = $Coordinate.version })) {
        $value = Get-MavenValue $project $item.tag $ns
        if (!$value -and $null -ne $parent) { $value = Get-MavenValue $parent $item.tag $ns }
        if ($value -cne $item.value) { throw 'POM coordinate mismatch' }
    }
    $edges = @($project.SelectNodes('m:parent | m:dependencies/m:dependency | m:dependencyManagement/m:dependencies/m:dependency[m:scope="import"]', $ns))
    foreach ($edge in $edges) {
        if ((Get-MavenValue $edge 'scope' $ns) -eq 'test') { continue }
        $group = Get-MavenValue $edge 'groupId' $ns
        $artifact = Get-MavenValue $edge 'artifactId' $ns
        if (!(Get-Registry $group $artifact)) { continue }
        $version = Get-MavenValue $edge 'version' $ns
        if ($version -ceq '${project.version}' -or $version -ceq '${pom.version}') { $version = $Coordinate.version }
        if ($version -cmatch '^\$\{([A-Za-z][A-Za-z0-9_.-]{0,80})\}$') {
            $properties = $project.SelectSingleNode('m:properties', $ns)
            if ($null -ne $properties) { $version = Get-MavenValue $properties $Matches[1] $ns }
        }
        Add-Coordinate $group $artifact $version
    }
    return (Get-MavenValue $project 'packaging' $ns)
}

function Read-Component([hashtable]$Coordinate) {
    $script:current = "$($Coordinate.group):$($Coordinate.artifact):$($Coordinate.version)"
    $stem = "$($Coordinate.artifact)-$($Coordinate.version)"
    $packageUrl = $registries[$Coordinate.registry] + '/' + $Coordinate.group.Replace('.', '/') +
        '/' + $Coordinate.artifact + '/' + [uri]::EscapeDataString($Coordinate.version)
    $script:stage = 'POM'
    $pom = Read-PackageBytes "$packageUrl/$([uri]::EscapeDataString("$stem.pom"))" $script:packageAuth 2MB
    $packaging = Read-Pom $pom $Coordinate
    Save-Library $Coordinate "$stem.pom" $pom
    $script:stage = 'Gradle module metadata'
    $module = Read-PackageBytes "$packageUrl/$([uri]::EscapeDataString("$stem.module"))" $script:packageAuth 2MB -Optional
    $artifacts = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
    if ($null -ne $module) {
        $data = ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($module)) -AsHashtable -Depth 32
        $component = $data['component']
        if ($data['formatVersion'] -cne '1.1' -or $null -eq $component -or
            $component['group'] -cne $Coordinate.group -or $component['module'] -cne $Coordinate.artifact -or
            $component['version'] -cne $Coordinate.version) { throw 'Module identity mismatch' }
        foreach ($variant in $data['variants']) {
            $attributes = $variant['attributes']
            if ($null -ne $attributes -and $attributes['org.gradle.category'] -eq 'documentation') { continue }
            if ($null -ne $variant['available-at']) { throw 'External Gradle variant' }
            foreach ($dependency in $variant['dependencies']) {
                $group = $dependency['group']
                $artifact = $dependency['module']
                if (!(Get-Registry $group $artifact)) { continue }
                $version = $dependency['version']
                $selected = ''
                if ($null -ne $version) {
                    foreach ($constraint in @('strictly', 'requires', 'prefers')) {
                        if ($version[$constraint]) { $selected = $version[$constraint]; break }
                    }
                }
                Add-Coordinate $group $artifact $selected
            }
            foreach ($file in $variant['files']) {
                $name = $file['url']
                if ($name -cnotmatch ('^' + [regex]::Escape($stem) + '(?:-[a-zA-Z0-9_.-]{1,80})?\.(?:aar|jar)$')) {
                    throw 'Unsupported module artifact path'
                }
                if ($artifacts.ContainsKey($name)) {
                    $existing = $artifacts[$name]
                    if ($existing['sha256'] -cne $file['sha256'] -or $existing['size'] -ne $file['size']) {
                        throw 'Conflicting artifact claims'
                    }
                } else { $artifacts.Add($name, $file) }
            }
        }
        Save-Library $Coordinate "$stem.module" $module
    }
    if ($artifacts.Count -eq 0 -and $packaging -ne 'pom') {
        if (!$packaging) { $packaging = 'jar' }
        if ($packaging -cnotin @('aar', 'jar')) { throw 'Unsupported Maven packaging' }
        $artifacts.Add("$stem.$packaging", $null)
    }
    foreach ($name in $artifacts.Keys) {
        $script:stage = 'library archive'
        $bytes = Read-PackageBytes "$packageUrl/$([uri]::EscapeDataString($name))" $script:packageAuth 64MB
        if ($bytes.Length -lt 4 -or $bytes[0] -ne 80 -or $bytes[1] -ne 75 -or
            $bytes[2] -ne 3 -or $bytes[3] -ne 4) { throw 'Invalid library archive' }
        $claim = $artifacts[$name]
        if ($null -ne $claim) {
            if ($null -ne $claim['size'] -and $claim['size'] -ne $bytes.Length) { throw 'Library size mismatch' }
            if ($claim['sha256'] -and $claim['sha256'] -ne
                [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))) { throw 'Library hash mismatch' }
        }
        Save-Library $Coordinate $name $bytes
    }
    $coordinates.Add($Coordinate)
}

function Save-Result([string]$Status) {
    if (!$run) { return }
    $result = [ordered]@{
        schema = 'oneos-local-package-mirror/v1'; status = $Status; seedSha256 = $seedSha
        mirror = 'maven'; coordinates = $coordinates.ToArray(); files = $files.ToArray()
        stage = $script:stage; httpStatus = $script:httpStatus; coordinate = $script:current
    }
    [IO.File]::WriteAllText((Join-Path $run 'receipt.json'), ($result | ConvertTo-Json -Depth 8))
}

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    if (!$IsWindows -or ![System.Windows.Forms.SystemInformation]::UserInteractive -or
        [Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA') { throw 'Interactive STA required' }
    foreach ($directory in @($root, (Join-Path $root 'out'), $base)) {
        if (([IO.File]::GetAttributes($directory) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Local output path must not be a reparse point'
        }
    }
    $seedBytes = [IO.File]::ReadAllBytes($seedPath)
    if ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($seedBytes)) -ne $seedSha) {
        throw 'Seed manifest changed'
    }
    $manifest = ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($seedBytes)) -AsHashtable
    foreach ($seed in $manifest.seeds) {
        if ($seed.registry -cne (Get-Registry $seed.group $seed.artifact)) { throw 'Unexpected seed route' }
        if ($seed.selection -eq 'strictly') { $strictPins.Add("$($seed.group):$($seed.artifact)", $seed.version) }
    }
    foreach ($seed in $manifest.seeds) { Add-Coordinate $seed.group $seed.artifact $seed.version }
    if ($pending.Count -ne 18 -or $strictPins.Count -ne 17) { throw 'Unexpected seed count' }
    if ($CheckLocalSetup) {
        Write-Output 'Local setup verified: WinForms, exact seed manifest, 18 package routes. No prompt or network.'
        exit 0
    }

    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'OneOS package download'
    $form.ClientSize = [Drawing.Size]::new(535, 161)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $label = [System.Windows.Forms.Label]::new()
    $label.SetBounds(15, 12, 500, 48)
    $label.Text = "Paste a GitHub classic token with only read:packages selected.`r`nThis box is masked. The token is used only to fetch the OneOS libraries."
    $field = [System.Windows.Forms.TextBox]::new()
    $field.SetBounds(15, 65, 500, 24)
    $field.UseSystemPasswordChar = $true
    $field.MaxLength = 40
    $download = [System.Windows.Forms.Button]::new()
    $download.SetBounds(272, 110, 150, 33)
    $download.Text = 'Download libraries'
    $download.DialogResult = 'OK'
    $download.Enabled = $false
    $cancel = [System.Windows.Forms.Button]::new()
    $cancel.SetBounds(430, 110, 85, 33)
    $cancel.Text = 'Cancel'
    $cancel.DialogResult = 'Cancel'
    $field.Add_TextChanged({ $download.Enabled = [regex]::IsMatch($field.Text, '\Aghp_[A-Za-z0-9]{36}\z') })
    $form.Controls.AddRange(@($label, $field, $download, $cancel))
    $form.AcceptButton = $download
    $form.CancelButton = $cancel
    $form.ActiveControl = $field
    if ($form.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $token = $field.Text
    $field.Clear()
    $form.Dispose()
    $form = $null
    if (![regex]::IsMatch($token, '\Aghp_[A-Za-z0-9]{36}\z')) { throw 'Invalid classic token format' }
    $run = Join-Path $base ('mirror-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($run) | Out-Null

    $script:stage = 'GitHub account authentication'
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $handler.UseCookies = $false
    $handler.UseProxy = $false
    $script:client = [Net.Http.HttpClient]::new($handler)
    $script:client.DefaultRequestHeaders.UserAgent.ParseAdd('OneOS-Package-Prefetch/1.0')
    $identity = Read-PackageBytes 'https://api.github.com/user' (
        [Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)) 128KB -CheckScope
    $script:stage = 'GitHub login field'
    $username = (ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($identity)) -AsHashtable)['login']
    [Array]::Clear($identity, 0, $identity.Length)
    $identity = $null
    if ($username -cnotmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,38}$') { throw 'Invalid GitHub login metadata' }
    $script:stage = 'Maven authorization setup'
    $basic = [Text.Encoding]::UTF8.GetBytes("${username}:${token}")
    try {
        $script:packageAuth = [Net.Http.Headers.AuthenticationHeaderValue]::new('Basic', [Convert]::ToBase64String($basic))
    } finally {
        [Array]::Clear($basic, 0, $basic.Length)
        $username = $null
        $token = $null
    }
    while ($pending.Count -ne 0) { Read-Component ($pending.Dequeue()) }
    $script:stage = 'complete'
    $script:current = ''
    $script:httpStatus = 0
    Save-Result 'PASS'
    Write-Output "Downloaded $($coordinates.Count) OneOS library versions. The local files are ready for Gradle."
} catch {
    # Do not expose raw exception messages, HTTP headers/body, account or token.
    $status = "Stopped at $($script:stage)."
    if ($script:current) { $status += "`r`n$($script:current)" }
    if ($script:httpStatus -ge 300) { $status += "`r`nHTTP $($script:httpStatus)." }
    try { Save-Result 'FAILED' } catch {}
    [Console]::Error.WriteLine($status)
    exit 1
} finally {
    $token = $null
    $username = $null
    $script:packageAuth = $null
    if ($null -ne $field -and !$field.IsDisposed) { $field.Clear() }
    if ($null -ne $form) { $form.Dispose() }
    if ($null -ne $script:client) { $script:client.Dispose() }
    if ($null -ne $handler) { $handler.Dispose() }
}
