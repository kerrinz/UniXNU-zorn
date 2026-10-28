# Windows PowerShell 5.1+. Fixed K80 touch identity probe; no Python required.
[CmdletBinding()]
param([switch]$CheckOnly, [switch]$CollectOnly)
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$serial = '92988a43'
$bootHash = 'bce3bdbe437455d7ed4049539b2881556fa8f4aeb89216b583620203838ba414'
$bootstrapHash = 'ee6681fd77ba97a3756a32d82a5d6487ba19428d9cf3cbc6c4c8fc4e5ac88548'
$root = $PSScriptRoot
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Save-Text([string]$Path, [string]$Text) {
    [IO.File]::WriteAllText($Path, $Text, $script:utf8)
}
function File-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Quote-Argument([string]$Value) {
    # Windows CommandLineToArgv/CRT quoting, including trailing backslashes.
    return '"' + ([regex]::Replace($Value, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}
function Find-Tool([string]$Name) {
    foreach ($path in @((Join-Path $root ($Name + '.exe')), (Join-Path $root ('platform-tools\' + $Name + '.exe')))) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return (Get-Command ($Name + '.exe') -CommandType Application -ErrorAction Stop).Source
}
function Invoke-Tool([string]$Exe, [string[]]$Arguments, [int]$Seconds = 20) {
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Exe
    $info.Arguments = ($Arguments | ForEach-Object { Quote-Argument $_ }) -join ' '
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $proc = New-Object Diagnostics.Process
    $proc.StartInfo = $info
    try {
        $null = $proc.Start()
        $stdout = $proc.StandardOutput.ReadToEndAsync()
        $stderr = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit($Seconds * 1000)) {
            $proc.Kill()
            $null = $proc.WaitForExit(5000)
            throw "Tool timeout after ${Seconds}s: $Exe $($info.Arguments)"
        }
        $output = $stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()
        if ($proc.ExitCode -ne 0) { throw "Tool exit $($proc.ExitCode): $Exe $($info.Arguments)`n$output" }
        return $output
    } finally { $proc.Dispose() }
}
function Adb([string[]]$Arguments, [int]$Seconds = 20) {
    return Invoke-Tool $script:adb (@('-s', $serial) + $Arguments) $Seconds
}
function Fastboot([string[]]$Arguments, [int]$Seconds = 20) {
    return Invoke-Tool $script:fastboot (@('-s', $serial) + $Arguments) $Seconds
}
function Adb-State {
    $listing = Invoke-Tool $script:adb @('devices')
    if ($listing -match '(?m)^92988a43\s+(\S+)') { return $Matches[1] }
    return ''
}
function Fastboot-Visible {
    return (Invoke-Tool $script:fastboot @('devices')) -match '(?m)^92988a43\s+fastboot\s*$'
}
function Verify-Recovery {
    if ((Adb-State) -ne 'recovery') { throw 'Exact K80 must be in recovery, not Android.' }
    if ((Adb @('get-serialno')).Trim() -ne $serial) { throw 'Serial mismatch.' }
    if ((Adb @('shell', 'getprop', 'ro.product.device')).Trim() -ne 'zorn') { throw 'Recovery product mismatch.' }
    if ((Adb @('shell', 'getprop', 'ro.boot.slot_suffix')).Trim() -ne '_b') { throw 'Recovery slot must be _b.' }
}
function Verify-Fastboot {
    if (-not (Fastboot-Visible)) { throw 'K80 is not in fastboot.' }
    if ((Fastboot @('getvar', 'product')) -notmatch '(?m)(?:^|\s)product:\s*zorn\s*$') { throw 'Fastboot product mismatch.' }
    if ((Fastboot @('getvar', 'current-slot')) -notmatch '(?m)(?:^|\s)current-slot:\s*b\s*$') { throw 'Fastboot slot must be b.' }
}
function Wait-Recovery {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt 360) {
        $state = Adb-State
        if ($state -eq 'recovery') { Verify-Recovery; return }
        if ($state -ne '') { throw "Unexpected K80 adb state: $state; stopping." }
        Start-Sleep -Seconds 2
    }
    throw 'No recovery within 360s. No further reboot attempted. Return the ZIP, including this failure.'
}
function Read-Page([string]$Partition, [int]$Skip, [string]$Destination) {
    # Only these two exact read ranges are supported. adb pull preserves binary bytes.
    if (-not (($Partition -eq 'userdata' -and $Skip -eq 2291712) -or ($Partition -eq 'misc' -and $Skip -eq 0))) {
        throw 'Read range rejected.'
    }
    $null = Adb @('shell', "dd if=/dev/block/by-name/$Partition of=/tmp/unixnu-host-read.bin bs=4096 skip=$Skip count=1")
    $null = Adb @('pull', '/tmp/unixnu-host-read.bin', $Destination)
    if ((Get-Item -LiteralPath $Destination).Length -ne 4096) { throw 'Expected exactly 4096 bytes.' }
}
function Prepare-BCB {
    Verify-Recovery
    $before = Join-Path $script:runDir 'misc-before.bin'
    Read-Page 'misc' 0 $before
    $page = [IO.File]::ReadAllBytes($before)
    [Array]::Clear($page, 0, 864)
    [Text.Encoding]::ASCII.GetBytes("boot-recovery`0").CopyTo($page, 0)
    [Text.Encoding]::ASCII.GetBytes("recovery`n").CopyTo($page, 64)
    $source = Join-Path $script:runDir 'recovery-bcb.bin'
    [IO.File]::WriteAllBytes($source, $page)
    $null = Adb @('push', $source, '/tmp/unixnu-recovery-bcb.bin')
    $copied = Join-Path $script:runDir 'bcb-upload.bin'
    $null = Adb @('pull', '/tmp/unixnu-recovery-bcb.bin', $copied)
    if ((File-Hash $source) -ne (File-Hash $copied)) { throw 'BCB RAM upload mismatch; no partition write attempted.' }
    $null = Adb @('shell', 'dd if=/tmp/unixnu-recovery-bcb.bin of=/dev/block/by-name/misc bs=4096 count=1 conv=notrunc')
    $after = Join-Path $script:runDir 'misc-after.bin'
    Read-Page 'misc' 0 $after
    if ((File-Hash $source) -ne (File-Hash $after)) { throw 'BCB readback mismatch; no boot attempted.' }
    $script:record.host_recovery_bcb_verified = $true
    Save-Text (Join-Path $script:runDir 'bcb.json') (@{
        changed_prefix_bytes = 864; tail_preserved = $true; readback_verified = $true
        before_sha256 = File-Hash $before; after_sha256 = File-Hash $after
    } | ConvertTo-Json)
}
function Decode-Log([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $magic = [Text.Encoding]::ASCII.GetString($bytes, 0, 8)
    $formats = @{ ZORNLOG1 = @(510,8); ZORNLOG2 = @(340,12); ZORNLOG3 = @(180,12)
        ZORNLOG4 = @(172,12); ZORNLOG5 = @(162,12); ZORNLOG6 = @(140,12)
        ZORNLOG7 = @(136,12); ZORNLOG8 = @(134,12); ZORNLOG9 = @(98,12)
        ZORNLOGA = @(96,12); ZORNLOGB = @(92,12) }
    if (-not $formats.ContainsKey($magic)) { throw "Unknown log magic: $magic. Raw block is preserved." }
    $capacity, $width = $formats[$magic]
    $count = [BitConverter]::ToUInt32($bytes, 8)
    $next = [BitConverter]::ToUInt32($bytes, 12)
    $ring = $magic -ne 'ZORNLOG1'
    if ($count -gt $capacity -or ($ring -and ($next -ge $capacity -or ($count -lt $capacity -and $next -ne $count)))) {
        throw 'Invalid log ring header; raw block preserved.'
    }
    $start = 0
    if ($ring -and $count -eq $capacity) { $start = $next }
    $stages = @()
    for ($index = 0; $index -lt $count; $index++) {
        $slot = ($start + $index) % $capacity
        $stage = [Text.Encoding]::ASCII.GetString($bytes, (16 + $slot * $width), $width).Split([char]0)[0]
        if ($stage -match '[^\x20-\x7e]') { throw 'Non-ASCII checkpoint; raw block preserved.' }
        if ($stage.Length -gt 0) { $stages += $stage }
    }
    $text = "$magic`r`n" + ($stages -join ' | ')
    $first = [Array]::IndexOf($stages, 'USRBEGIN')
    $last = [Array]::IndexOf($stages, 'USREND')
    if ($first -ge 0 -and $last -gt ($first + 1)) {
        $text += "`r`nUser report:`r`n" + ($stages[($first + 1)..($last - 1)] -join '')
    }
    Save-Text (Join-Path $script:runDir 'checkpoints.txt') ($text + "`r`n")
    Write-Host $text
}

if ($CheckOnly -and $CollectOnly) { throw 'Choose only one mode.' }
$image = Join-Path $root 'boot.img'
$bootstrap = Join-Path $root 'recovery-bootstrap.img'
if ((File-Hash $image) -ne $bootHash) { throw 'boot.img SHA256 mismatch; no USB action.' }
if ((File-Hash $bootstrap) -ne $bootstrapHash) { throw 'Recovery bootstrap SHA256 mismatch; no USB action.' }
if ($CheckOnly) { Write-Host 'Pinned image hashes OK. No USB access.'; exit 0 }
$adb = Find-Tool 'adb'
$fastboot = Find-Tool 'fastboot'
$null = New-Item -ItemType Directory -Force -Path (Join-Path $root 'logs')
# Exclusive host lock prevents two copies using the same package simultaneously.
$lock = [IO.File]::Open((Join-Path $root 'test.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$runDir = Join-Path $root ('logs\' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-bce3bdbe')
$null = New-Item -ItemType Directory -Path $runDir
$record = [ordered]@{ status = 'preflight'; serial = $serial; product = 'zorn'; slot = 'b'
    started_at = (Get-Date).ToString('o'); boot_sha256 = $bootHash
    collect_only = [bool]$CollectOnly; kernel_log_changed = $null
    image_attribution = 'not yet booted'; host_recovery_bcb_verified = $false }
$failed = $false
try {
    Copy-Item -LiteralPath (Join-Path $root 'manifest.json') -Destination $runDir
    if (-not $CollectOnly) {
        $state = Adb-State
        if ($state -eq '') {
            Verify-Fastboot
            Write-Host 'Booting pinned recovery bootstrap. Wait for recovery (up to 360s).'
            Save-Text (Join-Path $runDir 'bootstrap-fastboot.txt') (Fastboot @('boot', $bootstrap) 60)
            Wait-Recovery
        } elseif ($state -ne 'recovery') { throw "Unexpected K80 adb state: $state" }
        Verify-Recovery
        Read-Page 'userdata' 2291712 (Join-Path $runDir 'preboot-checkpoints.bin')
        $record.preboot_log_sha256 = File-Hash (Join-Path $runDir 'preboot-checkpoints.bin')
        Prepare-BCB
        $null = Adb @('reboot', 'bootloader')
        $timer = [Diagnostics.Stopwatch]::StartNew()
        while (-not (Fastboot-Visible)) {
            if ($timer.Elapsed.TotalSeconds -ge 30) { throw 'Fastboot did not appear within 30s.' }
            Start-Sleep -Seconds 1
        }
        Verify-Fastboot
        $record.status = 'booting'
        Save-Text (Join-Path $runDir 'run.json') ($record | ConvertTo-Json -Depth 8)
        Write-Host 'Temporary boot: FT3683 identity probe. No GUI or touch response expected.'
        Save-Text (Join-Path $runDir 'fastboot.txt') (Fastboot @('boot', $image) 60)
        $record.boot_completed_at = (Get-Date).ToString('o')
        Write-Host 'Waiting for automatic recovery (up to 360s). Keep USB connected.'
        Wait-Recovery
    }
    Verify-Recovery
    $log = Join-Path $runDir 'checkpoints.bin'
    Read-Page 'userdata' 2291712 $log
    $record.kernel_log_sha256 = File-Hash $log
    if ($CollectOnly) {
        $record.status = 'collected_unbound'
        $record.image_attribution = 'Unknown: collection does not prove this image ran or this log is new.'
    } else {
        $record.status = 'recovered'
        $record.kernel_log_changed = $record.kernel_log_sha256 -ne $record.preboot_log_sha256
        $record.image_attribution = 'Pinned boot completed; compare pre/post logs. Changed log alone does not prove touch success.'
        if (-not $record.kernel_log_changed) { Write-Warning 'UNCHANGED LOG: do not treat it as this image result.' }
    }
    try { Decode-Log $log } catch { $record.decode_error = $_.Exception.Message; Write-Warning $record.decode_error }
} catch {
    $failed = $true
    $record.status = 'failed'
    $record.error = $_.Exception.Message
    Write-Warning $record.error
} finally {
    try {
        $record.finished_at = (Get-Date).ToString('o')
        Save-Text (Join-Path $runDir 'run.json') ($record | ConvertTo-Json -Depth 8)
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = $runDir + '.zip'
        [IO.Compression.ZipFile]::CreateFromDirectory($runDir, $zip)
        Write-Host "Return this log bundle: $zip"
    } finally { $lock.Dispose() }
}
if ($failed) { exit 1 }
