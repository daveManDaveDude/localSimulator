#requires -Version 7.4
param(
    [ValidateSet('build', 'self-check', 'runtime-preflight')]
    [string]$Mode = 'build'
)

$ErrorActionPreference = 'Stop'
$modeBudgetSeconds = switch ($Mode) {
    'build' { 180.0 }
    'self-check' { 10.0 }
    'runtime-preflight' { 30.0 }
}
$qpcFrequency = [Diagnostics.Stopwatch]::Frequency
$startQpc = [Diagnostics.Stopwatch]::GetTimestamp()
$deadlineQpc = $startQpc + [long][Math]::Ceiling($modeBudgetSeconds * $qpcFrequency)
$lexicalRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$root = $lexicalRoot
$buildRoot = Join-Path $root 'docs\milestones\artifacts\Teignmouth-float32-topology\build-3'
$python = Join-Path $root 'pipeline\.venv\Scripts\python.exe'
$supervisor = Join-Path $root 'pipeline\scripts\run_teignmouth_float32_build3.py'
$baseEvidence = switch ($Mode) {
    'build' { $buildRoot }
    'self-check' { Join-Path $root '.codex\build3-supervisor-selfcheck-retry-7' }
    'runtime-preflight' { Join-Path $root '.codex\build3-runtime-preflight' }
}
$ownedRunLeaf = switch ($Mode) {
    'build' { Join-Path $buildRoot 'run-1' }
    'self-check' { Join-Path $baseEvidence 'run-1' }
    'runtime-preflight' { Join-Path $baseEvidence 'run-1' }
}
$callerPath = Join-Path $baseEvidence 'caller-invocation.json'
$callerFailurePath = if ($Mode -eq 'self-check') { Join-Path $baseEvidence 'caller-invocation.failure.json' } else { $null }
$handoffPath = switch ($Mode) {
    'build' { Join-Path $buildRoot 'dispatch-handoff.json' }
    'self-check' { Join-Path $baseEvidence 'self-check-handoff.json' }
    'runtime-preflight' { Join-Path $baseEvidence 'runtime-preflight-handoff.json' }
}
$consumedPath = switch ($Mode) {
    'build' { Join-Path $buildRoot 'dispatch-handoff.consumed.json' }
    'self-check' { Join-Path $baseEvidence 'self-check-handoff.consumed.json' }
    'runtime-preflight' { Join-Path $baseEvidence 'runtime-preflight-handoff.consumed.json' }
}
$scriptStartPath = switch ($Mode) {
    'build' { Join-Path $buildRoot 'supervisor-script-start.json' }
    'self-check' { Join-Path $baseEvidence 'supervisor-script-start.json' }
    'runtime-preflight' { Join-Path $baseEvidence 'supervisor-script-start.json' }
}
$stdoutPath = Join-Path $baseEvidence 'supervisor.stdout.log'
$stderrPath = Join-Path $baseEvidence 'supervisor.stderr.log'
$launcherArguments = switch ($Mode) {
    'build' { @('-B', $supervisor) }
    'self-check' { @('-B', $supervisor, '--self-check') }
    'runtime-preflight' { @('-B', $supervisor, '--runtime-preflight-only') }
}

function Assert-NoReparsePath([string]$Path, [switch]$AllowMissingSuffix) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $pathRoot = [IO.Path]::GetPathRoot($fullPath)
    $currentPath = $pathRoot
    $parts = $fullPath.Substring($pathRoot.Length).Split(
        [IO.Path]::DirectorySeparatorChar,
        [StringSplitOptions]::RemoveEmptyEntries
    )
    for ($index = 0; $index -lt $parts.Length; $index++) {
        $currentPath = Join-Path $currentPath $parts[$index]
        if (-not (Test-Path -LiteralPath $currentPath)) {
            if ($AllowMissingSuffix) { break }
            throw "Fixed path component is unavailable: $currentPath"
        }
        $entry = Get-Item -LiteralPath $currentPath -Force
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Fixed path uses a reparse point: $currentPath"
        }
    }
    if ((Test-Path -LiteralPath $fullPath) -and
        (Resolve-Path -LiteralPath $fullPath).Path -ne $fullPath) {
        throw "Resolved path differs from fixed lexical path: $fullPath"
    }
}

function Get-QpcValue {
    $value = [long]0
    if (-not [TeignmouthBuild3Native]::QueryPerformanceCounter([ref]$value)) {
        throw 'QueryPerformanceCounter failed.'
    }
    return $value
}

function Get-RemainingMilliseconds([long]$Deadline, [long]$Frequency) {
    $remaining = [Math]::Floor(($Deadline - (Get-SafeQpcValue)) * 1000.0 / $Frequency)
    return [int][Math]::Max(0, [Math]::Min([int]::MaxValue, $remaining))
}

function Get-SafeQpcValue {
    if ($nativeClockReady) { return Get-QpcValue }
    return [Diagnostics.Stopwatch]::GetTimestamp()
}

function Write-ExclusiveJson([string]$Path, [hashtable]$Record) {
    $stream = [IO.File]::Open(
        $Path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::Read
    )
    $writeError = $null
    $closeError = $null
    try {
        $data = [Text.UTF8Encoding]::new($false).GetBytes(
            ($Record | ConvertTo-Json -Depth 12) + "`n"
        )
        $stream.Write($data, 0, $data.Length)
        $stream.Flush($true)
    }
    catch { $writeError = $_ }
    finally {
        $callerPersistenceState.stageBeforeClose = $callerPersistenceState.stage
        $callerPersistenceState.stage = 'close-exclusive-record'
        try { $stream.Dispose() }
        catch { $closeError = $_ }
    }
    if ($null -ne $writeError) {
        if ($null -ne $closeError) { $callerPersistenceState.secondaryCloseFailure = New-CallerFailure $closeError 'close-exclusive-record' }
        $callerPersistenceState.stage = $callerPersistenceState.stageBeforeClose
        throw $writeError
    }
    if ($null -ne $closeError) { throw $closeError }
}

function Update-OwnedJson([string]$Path, [hashtable]$Record, [ValidateSet('Caller','Handoff')][string]$RecordKind) {
    $pendingPath = $Path + '.update'
    $callerPersistenceState.recordKind = $RecordKind
    $callerPersistenceState.destinationPath = $Path
    $callerPersistenceState.pendingPath = $pendingPath
    $callerPersistenceState.stage = 'validate-owned-destination'
    Assert-OwnedRecordDestination $RecordKind $Path $Record
    Assert-NoReparsePath $pendingPath -AllowMissingSuffix
    if (Test-Path -LiteralPath $pendingPath) { throw "Stale or unowned $RecordKind update exists: $pendingPath" }
    $callerPersistenceState.stage = 'create-exclusive-pending'
    $stream = [IO.File]::Open($pendingPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $pendingOwned = $true
    $writeError = $null
    $closeError = $null
    try {
        $callerPersistenceState.stage = 'serialize-pending'
        $data = [Text.UTF8Encoding]::new($false).GetBytes(
            ($Record | ConvertTo-Json -Depth 12) + "`n"
        )
        $callerPersistenceState.stage = 'write-and-flush-pending'
        $stream.Write($data, 0, $data.Length)
        $stream.Flush($true)
    }
    catch { $writeError = $_ }
    finally {
        $callerPersistenceState.stageBeforeClose = $callerPersistenceState.stage
        $callerPersistenceState.stage = 'close-pending'
        try { $stream.Dispose() }
        catch { $closeError = $_ }
    }
    if ($null -ne $writeError) {
        if ($null -ne $closeError) {
            $callerPersistenceState.secondaryCloseFailure = New-CallerFailure $closeError 'close-pending'
        }
        $callerPersistenceState.stage = $callerPersistenceState.stageBeforeClose
        throw $writeError
    }
    if ($null -ne $closeError) { throw $closeError }
    $callerPersistenceState.stage = 'revalidate-before-move'
    if (-not $pendingOwned) { throw "Exclusive pending ownership was not established: $pendingPath" }
    Assert-OwnedRecordDestination $RecordKind $Path $Record
    Assert-NoReparsePath $pendingPath
    if (-not (Test-Path -LiteralPath $pendingPath -PathType Leaf)) { throw "Owned pending file is missing or not a file: $pendingPath" }
    $callerPersistenceState.stage = 'same-directory-move-overwrite'
    # Explicit supported overload; no delete/truncate or alternate-method retry.
    # This does not establish crash atomicity or power-loss durability.
    [IO.File]::Move($pendingPath, $Path, $true)
    if ($RecordKind -eq 'Handoff') { $script:handoffLauncherBound = $true }
    $callerPersistenceState.stage = 'idle'
}

function Assert-OwnedRecordDestination([string]$RecordKind, [string]$Path, [hashtable]$Record) {
    switch -CaseSensitive ($RecordKind) {
        'Caller' { Assert-OwnedCallerDestination $Path $Record; return }
        'Handoff' { Assert-OwnedHandoffDestination $Path $Record; return }
        default { throw "Unknown owned-record kind: $RecordKind" }
    }
}

function Assert-OwnedCallerDestination([string]$Path, [hashtable]$Record) {
    if (-not $callerRecordOwned -or -not $callerParentValidated -or
        [IO.Path]::GetFullPath($Path) -cne $callerPath) {
        throw 'Caller update does not own the exact fixed destination.'
    }
    Assert-NoReparsePath $baseEvidence
    Assert-NoReparsePath $Path
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw 'Owned caller destination is missing or not a file.' }
    $existing = [IO.File]::ReadAllText($Path) | ConvertFrom-Json -AsHashtable
    if ($Record.schema -cne 'teignmouth-build3-caller-record-v2' -or
        $Record.wrapperPid -ne $PID -or
        $Record.startQpc -ne $startQpc -or $Record.mode -cne $Mode -or
        $existing.schema -cne 'teignmouth-build3-caller-record-v2' -or
        $existing.wrapperPid -ne $PID -or
        $existing.startQpc -ne $startQpc -or $existing.mode -ne $Mode) {
        throw 'Caller destination no longer carries this invocation ownership.'
    }
}

function Test-ExactRecordValue($Expected, $Actual) {
    if ($null -eq $Expected) { return $null -eq $Actual }
    if ($Expected -is [string]) { return ($Actual -is [string]) -and ([string]$Actual -ceq $Expected) }
    if ($Expected -is [bool]) { return ($Actual -is [bool]) -and ([bool]$Actual -eq $Expected) }
    if ($Expected -is [double] -or $Expected -is [single] -or $Expected -is [decimal]) {
        if ($Actual -isnot [double] -and $Actual -isnot [single] -and $Actual -isnot [decimal]) { return $false }
        return ([double]$Actual).Equals([double]$Expected)
    }
    $integralTypes = @([sbyte],[byte],[int16],[uint16],[int32],[uint32],[int64],[uint64])
    if ($Expected.GetType() -in $integralTypes) {
        if ($Actual.GetType() -notin $integralTypes) { return $false }
        try { return ([decimal]$Actual -eq [decimal]$Expected) }
        catch { return $false }
    }
    return ($Actual.GetType() -eq $Expected.GetType()) -and ($Actual -ceq $Expected)
}

function Assert-ExactHandoffRecord($Expected, $Actual, [string]$Label) {
    if ($Expected -isnot [System.Collections.IDictionary] -or
        $Actual -isnot [System.Collections.IDictionary] -or
        $Expected.Count -ne $Actual.Count) { throw "$Label handoff has a malformed key set." }
    $expectedKeys = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($key in $Expected.Keys) { [void]$expectedKeys.Add([string]$key) }
    foreach ($key in $Actual.Keys) {
        if (-not $expectedKeys.Contains([string]$key)) { throw "$Label handoff has an unexpected or case-distinct key: $key" }
        if (-not (Test-ExactRecordValue $Expected[[string]$key] $Actual[[string]$key])) {
            throw "$Label handoff value differs from its trusted identity: $key"
        }
    }
}

function Get-TrustedPreparedHandoff {
    return @{
        schema = 'teignmouth-build3-parent-handoff-v2'
        mode = $Mode
        oneUse = $true
        phase = [string]$callerRecord.phase
        nonce = [string]$handoffNonce
        clockDomain = 'windows-qpc'
        qpcFrequency = [long]$qpcFrequency
        startQpc = [long]$startQpc
        deadlineQpc = [long]$deadlineQpc
        budgetSeconds = [double]$modeBudgetSeconds
        wrapperPid = [int]$PID
        wrapperCreationFileTime = [long]$parentCreated
        wrapperImagePath = [string]$wrapperIdentity.imagePath
        wrapperImageSha256 = [string]$wrapperIdentity.imageSha256
        expectedSupervisorScript = [string][IO.Path]::GetFullPath($supervisor)
        launcherPath = [string][IO.Path]::GetFullPath($python)
        launcherSha256 = [string]$launcherHash
        baseInterpreterPath = [string]$baseInterpreter
        baseInterpreterSha256 = [string]$baseHash
        launcherPid = $null
        launcherCreationFileTime = $null
        launcherImagePath = $null
        launcherImageSha256 = $null
        inputManifestSha256 = $manifestSha
        externalRuntimeManifestSha256 = $externalSha
        reservedLedgerSnapshotSha256 = $snapshotSha
        standaloneAuthorizationSha256 = $authSha
        runtimeIdentitySha256 = $runtimeIdentitySha
        standalonePurpose = $standalonePurpose
        status = 'PREPARED'
    }
}

function Assert-OwnedHandoffDestination([string]$Path, [hashtable]$ProposedRecord) {
    $expectedPath = switch ($Mode) {
        'build' { Join-Path $buildRoot 'dispatch-handoff.json' }
        'self-check' { Join-Path $baseEvidence 'self-check-handoff.json' }
        'runtime-preflight' { Join-Path $baseEvidence 'runtime-preflight-handoff.json' }
    }
    $expectedPath = [IO.Path]::GetFullPath($expectedPath)
    if (-not $handoffRecordOwned -or -not $callerRecordOwned -or -not $callerParentValidated -or
        $handoffLauncherBound -or [IO.Path]::GetFullPath($Path) -cne $expectedPath -or
        [IO.Path]::GetFullPath($handoffPath) -cne $expectedPath) {
        throw 'Handoff update does not own the exact fixed, unconsumed destination.'
    }
    Assert-NoReparsePath $baseEvidence
    Assert-NoReparsePath $Path
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw 'Owned prepared handoff is missing or not a file.' }
    if (Test-Path -LiteralPath $consumedPath) { throw "Consumed handoff already exists: $consumedPath" }
    if (Test-Path -LiteralPath $scriptStartPath) { throw "Supervisor script-start marker already exists: $scriptStartPath" }
    if ([string]::IsNullOrWhiteSpace($handoffPreparedSha256) -or
        $null -eq $handoffPreparedSnapshot -or
        (Get-FileSha256BeforeDeadline $Path $deadlineQpc) -cne $handoffPreparedSha256) {
        throw 'Prepared handoff bytes differ from the exclusively created snapshot.'
    }
    $trustedPrepared = Get-TrustedPreparedHandoff
    Assert-ExactHandoffRecord $trustedPrepared $handoffPreparedSnapshot 'In-memory prepared'
    $persisted = [IO.File]::ReadAllText($Path) | ConvertFrom-Json -AsHashtable
    Assert-ExactHandoffRecord $handoffPreparedSnapshot $persisted 'Persisted prepared'
    if ((Get-FileSha256BeforeDeadline $Path $deadlineQpc) -cne $handoffPreparedSha256) {
        throw 'Prepared handoff changed while its identity was parsed.'
    }
    if ($ProposedRecord -isnot [System.Collections.IDictionary] -or
        $ProposedRecord.Count -ne $handoffPreparedSnapshot.Count) { throw 'Proposed launcher handoff has a malformed key set.' }
    $expectedKeys = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($key in $handoffPreparedSnapshot.Keys) { [void]$expectedKeys.Add([string]$key) }
    $allowedLauncherChanges = @('status','launcherPid','launcherCreationFileTime','launcherImagePath','launcherImageSha256')
    foreach ($key in $ProposedRecord.Keys) {
        if (-not $expectedKeys.Contains([string]$key)) { throw "Proposed handoff contains an unexpected or case-distinct key: $key" }
        if ($key -notin $allowedLauncherChanges -and
            -not (Test-ExactRecordValue $handoffPreparedSnapshot[$key] $ProposedRecord[$key])) {
            throw "Proposed handoff changed immutable field: $key"
        }
    }
    if (-not (Test-ExactRecordValue 'LAUNCHER_BOUND_BEFORE_RESUME' $ProposedRecord.status) -or
        -not $launcherCreated -or $launcherAssigned -or $launcherResumed -or
        $null -eq $processInfo -or $null -eq $launcherIdentity -or
        -not (Test-ExactRecordValue ([long]$processInfo.processId) $ProposedRecord.launcherPid) -or
        -not (Test-ExactRecordValue ([long]$launcherIdentity.creationFileTime) $ProposedRecord.launcherCreationFileTime) -or
        -not (Test-ExactRecordValue ([string]$launcherIdentity.imagePath) $ProposedRecord.launcherImagePath) -or
        -not (Test-ExactRecordValue ([string][IO.Path]::GetFullPath($python)) $ProposedRecord.launcherImagePath) -or
        -not (Test-ExactRecordValue ([string]$launcherIdentity.imageSha256) $ProposedRecord.launcherImageSha256) -or
        -not (Test-ExactRecordValue ([string]$launcherHash) $ProposedRecord.launcherImageSha256)) {
        throw 'Proposed handoff does not bind the verified, suspended, unassigned launcher.'
    }
}

function New-CallerFailure($Failure, [string]$Stage) {
    $inner = $Failure.Exception.InnerException
    return @{
        stage = $Stage
        exceptionType = $Failure.Exception.GetType().FullName
        message = $Failure.Exception.Message
        errorId = $Failure.FullyQualifiedErrorId
        innerExceptionType = if ($null -ne $inner) { $inner.GetType().FullName } else { $null }
        innerMessage = if ($null -ne $inner) { $inner.Message } else { $null }
        launcherCreated = $launcherCreated
        launcherAssigned = $launcherAssigned
        launcherResumed = $launcherResumed
    }
}

function Write-CallerTerminalFailure([hashtable]$Record) {
    $expectedRoot = Join-Path $root '.codex\build3-supervisor-selfcheck-retry-7'
    if (-not $callerRecordOwned -or -not $callerParentValidated -or $Mode -ne 'self-check' -or
        $baseEvidence -cne $expectedRoot -or
        $callerFailurePath -cne (Join-Path $expectedRoot 'caller-invocation.failure.json')) {
        throw 'Terminal fallback is restricted to the owned fixed self-check retry root.'
    }
    Assert-NoReparsePath $baseEvidence
    Assert-NoReparsePath $callerFailurePath -AllowMissingSuffix
    $Record.status = 'CALLER_PERSISTENCE_FAILURE'
    $Record.wrapperChosenExitCode = 2
    $Record.terminalCallerUpdatePersisted = $false
    $Record.terminalFailureRecordPath = $callerFailurePath
    Write-ExclusiveJson $callerFailurePath $Record
}

function Get-FileSha256BeforeDeadline([string]$Path, [long]$Deadline) {
    if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline before hashing $Path." }
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $buffer = New-Object byte[] (1024 * 1024)
        while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline while hashing $Path." }
            $null = $algorithm.TransformBlock($buffer, 0, $read, $buffer, 0)
        }
        $null = $algorithm.TransformFinalBlock([byte[]]@(), 0, 0)
        if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline after hashing $Path." }
        return [Convert]::ToHexString($algorithm.Hash).ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

function Get-JsonObjectBeforeDeadline([string]$Path, [long]$Deadline) {
    if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline before reading $Path." }
    $value = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
    if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline after reading $Path." }
    if ($value -isnot [System.Collections.IDictionary]) { throw "Expected JSON object at $Path." }
    return $value
}

function Assert-LocalCanonicalPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path) -or
        $Path.StartsWith('\\') -or $Path.StartsWith('//') -or $Path.StartsWith('\\?\') -or
        $Path.StartsWith('\\.\') -or $Path.Length -lt 3 -or $Path[1] -ne ':' -or
        $Path.Substring(2).Contains(':')) { throw "Path is not a supported local canonical path: $Path" }
    if ([IO.Path]::GetFullPath($Path) -cne $Path) { throw "Path is not lexically canonical: $Path" }
}

function Assert-ExternalPathBound([string]$Path, $Roots) {
    Assert-LocalCanonicalPath $Path
    $full = [IO.Path]::GetFullPath($Path)
    $matches = @($Roots | Where-Object {
        $base = [IO.Path]::GetFullPath([string]$_.path).TrimEnd('\') + '\'
        $full.StartsWith($base, [StringComparison]::OrdinalIgnoreCase) -or
            $full.Equals($base.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)
    })
    if ($matches.Count -ne 1) { throw "External path is not within exactly one frozen root: $Path" }
    return $matches[0].category
}

function Assert-ApprovedSearchPath([string]$Path, $Roots, [long]$Deadline) {
    Assert-LocalCanonicalPath $Path
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path)) {
        throw "Python/native search path is empty or relative: $Path"
    }
    if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline checking runtime search paths.' }
    $full = [IO.Path]::GetFullPath($Path)
    Assert-NoReparsePath $full
    if (-not (Test-Path -LiteralPath $full)) { throw "Runtime search path is unavailable: $full" }
    $repoPrefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    if ($full.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        $full.Equals($repoPrefix.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) { return }
    $null = Assert-ExternalPathBound $full $Roots
}

function Assert-FrozenProfileCandidate([string]$Path, $RepoMap, $ExternalMap, [long]$Deadline) {
    if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while binding finite-profile candidate.' }
    $full = [IO.Path]::GetFullPath($Path)
    Assert-NoReparsePath $full
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Profile candidate is not a regular file: $full" }
    $binding = $null
    $repoPrefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    if ($full.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        $relative = [IO.Path]::GetRelativePath($root, $full).Replace('\','/')
        if ($RepoMap.ContainsKey($relative)) { $binding = $RepoMap[$relative] }
    }
    if ($null -eq $binding -and $ExternalMap.ContainsKey($full)) { $binding = $ExternalMap[$full] }
    if ($null -eq $binding) { throw "Unbound finite-profile executable candidate: $full" }
    $info = Get-Item -LiteralPath $full
    $digest = Get-FileSha256BeforeDeadline $full $Deadline
    if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline after hashing finite-profile candidate: $full" }
    $after = Get-Item -LiteralPath $full
    if ($info.Length -ne $after.Length -or $info.LastWriteTimeUtc -ne $after.LastWriteTimeUtc -or
        $after.Length -ne [long]$binding.byteLength -or $digest -ne [string]$binding.sha256) {
        throw "Finite-profile candidate differs from its frozen binding: $full"
    }
}

function Assert-FiniteProfileZip([string]$Path, [long]$Deadline) {
    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    $archive = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $names = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($entry in $archive.Entries) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while validating finite-profile zip.' }
            $name = $entry.FullName.Replace('\','/').TrimEnd('/')
            $parts = $name.Split('/')
            if ([string]::IsNullOrWhiteSpace($name) -or $name.StartsWith('/') -or $name.Contains(':') -or
                $parts -contains '..' -or $parts -contains '.' -or $parts -contains '' -or
                -not $names.Add($name) -or $name -match '(?i)\.(pyd|dll|exe|ocx|cpl|zip|egg|whl)$') {
                throw "Unsupported or ambiguous finite-profile zip member: $name"
            }
            $unixType = (([uint32]$entry.ExternalAttributes -shr 16) -band 0xF000)
            if ($unixType -eq 0xA000) { throw "Zip symbolic link is unsupported: $name" }
            if ($entry.Name) {
                $stream = $entry.Open()
                try { if ($stream.ReadByte() -eq 0x4d -and $stream.ReadByte() -eq 0x5a) { throw "Zip contains PE executable data: $name" } }
                finally { $stream.Dispose() }
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after zip member header inspection.' }
            }
            if ($name -match '^(?i)(sitecustomize|usercustomize)(\.|/|$)') { throw "Python customization in zip is unsupported: $name" }
        }
    }
    finally { $archive.Dispose() }
}

function Test-FiniteStartupProfile([string]$ExternalManifestPath, [string]$RuntimeIdentityPath, [long]$Deadline, [hashtable]$Record, $RepoMap, $ExternalMap, $Roots, [string[]]$AdditionalPythonRoots) {
    $Record.finiteStartupProfileProgress = @{ stage = 'policy'; candidateCount = 0; bytesHashed = 0 }
    Save-Caller $Record
    if ([string]::IsNullOrWhiteSpace($env:SystemRoot) -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Finite profile requires the pinned AMD64 Windows runtime with SystemRoot.' }
    $identity = Get-JsonObjectBeforeDeadline $RuntimeIdentityPath $Deadline
    $expectedEnvironment = $identity.identity.environment
    if ($expectedEnvironment -isnot [System.Collections.IDictionary]) { throw 'Frozen identity has no exact environment map.' }
    $environmentNames = @('PATH','PYTHONPATH','PYTHONHOME','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','PYTHONUSERBASE','PYTHONPYCACHEPREFIX','PYTHONSAFEPATH','PYTHONPLATLIBDIR','PYTHONCASEOK','VIRTUAL_ENV','PROJ_DATA','PROJ_LIB','GDAL_DATA','GEOS_LIBRARY_PATH','GEOS_LIBDIR','SYSTEMROOT','PROCESSOR_ARCHITECTURE')
    foreach ($name in $environmentNames) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while comparing finite-profile environment.' }
        if (-not $expectedEnvironment.Contains($name) -or
            [string]$expectedEnvironment[$name] -cne [string][Environment]::GetEnvironmentVariable($name)) {
            throw "Runtime environment differs from the frozen finite-profile value: $name"
        }
    }
    foreach ($name in @('PYTHONHOME','PYTHONUSERBASE','PYTHONPYCACHEPREFIX','PYTHONSAFEPATH','PYTHONPLATLIBDIR','PYTHONCASEOK','GEOS_LIBDIR','GEOS_LIBRARY_PATH')) {
        if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($name))) { throw "Unsupported startup/native override: $name" }
    }
    foreach ($name in @('PROJ_DATA','PROJ_LIB','GDAL_DATA')) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) { Assert-ApprovedSearchPath $value $Roots $Deadline }
    }
    if ($env:PYTHONNOUSERSITE -notin @($null,'','1') -or $env:PYTHONDONTWRITEBYTECODE -notin @($null,'','1')) {
        throw 'Python site/cache environment is outside the finite profile.'
    }
    foreach ($name in [Environment]::GetEnvironmentVariables().Keys) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline checking inherited environment keys.' }
        if ([string]$name -match '^(?i)PYTHON' -and [string]$name -notin $environmentNames -and
            -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable([string]$name))) {
            throw "Unlisted nonempty Python startup override: $name"
        }
    }

    $baseRoot = Split-Path $baseInterpreter -Parent
    $venvRoot = Join-Path $root 'pipeline/.venv'
    $cfgCandidates = @(
        (Join-Path $venvRoot 'pyvenv.cfg'),
        (Join-Path (Split-Path $python -Parent) 'pyvenv.cfg'),
        (Join-Path (Split-Path $baseInterpreter -Parent) 'pyvenv.cfg')
    ) | Select-Object -Unique
    foreach ($cfg in $cfgCandidates) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline checking venv configuration candidates.' }
        if ($cfg -eq (Join-Path $venvRoot 'pyvenv.cfg')) { continue }
        if (Test-Path -LiteralPath $cfg) { throw "Ambiguous adjacent pyvenv.cfg is unsupported: $cfg" }
    }
    $cfgPath = Join-Path $venvRoot 'pyvenv.cfg'
    $cfgValues = Get-PyvenvPolicy $cfgPath $Deadline
    if ([IO.Path]::GetFullPath($cfgValues['home']) -ne [IO.Path]::GetFullPath((Split-Path $baseInterpreter -Parent))) {
        throw 'pyvenv.cfg does not match the pinned CPython 3.13.7 venv policy.'
    }
    foreach ($directory in @((Split-Path $python -Parent),(Split-Path $baseInterpreter -Parent),(Join-Path $baseRoot 'DLLs'))) {
        foreach ($name in @('python._pth','python313._pth')) {
            if (Test-Path -LiteralPath (Join-Path $directory $name)) { throw "Unsupported Python path override file: $(Join-Path $directory $name)" }
        }
    }
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::CurrentUser,[Microsoft.Win32.RegistryHive]::LocalMachine)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry32,[Microsoft.Win32.RegistryView]::Registry64)) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline checking PythonCore registry profile.' }
            $key = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive,$view)
            try {
                $pythonPathKey = $key.OpenSubKey('Software\Python\PythonCore\3.13\PythonPath',$false)
                if ($null -ne $pythonPathKey) {
                    try { if ($pythonPathKey.ValueCount -gt 0 -or $pythonPathKey.SubKeyCount -gt 0) { throw "Registry Python search path override is unsupported: $hive/$view" } }
                    finally { $pythonPathKey.Dispose() }
                }
                $installKey = $key.OpenSubKey('Software\Python\PythonCore\3.13\InstallPath',$false)
                if ($null -ne $installKey) {
                    try {
                        if ($installKey.SubKeyCount -gt 0 -or $installKey.ValueCount -gt 1) { throw "Ambiguous PythonCore install registry configuration: $hive/$view" }
                        if ($installKey.ValueCount -eq 1) {
                            $registeredHome = [string]$installKey.GetValue('')
                            if ([string]::IsNullOrWhiteSpace($registeredHome) -or [IO.Path]::GetFullPath($registeredHome) -ne [IO.Path]::GetFullPath($baseRoot)) { throw "PythonCore registry home differs from authenticated base: $hive/$view" }
                        }
                    }
                    finally { $installKey.Dispose() }
                }
            }
            finally { $key.Dispose() }
        }
    }

    $pythonRoots = [Collections.Generic.List[string]]::new()
    $nativeRoots = [Collections.Generic.List[string]]::new()
    $pythonPathSeen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $nativePathSeen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($path in @((Join-Path $root 'pipeline/scripts'),(Join-Path $baseRoot 'Lib'),(Join-Path $baseRoot 'DLLs'),(Join-Path $venvRoot 'Lib/site-packages'),(Join-Path $root 'pipeline'))) { $pythonRoots.Add([IO.Path]::GetFullPath($path)) }
    foreach ($path in $AdditionalPythonRoots) { if (-not [string]::IsNullOrWhiteSpace($path)) { $pythonRoots.Add([IO.Path]::GetFullPath($path)) } }
    foreach ($path in @((Split-Path $python -Parent),(Split-Path $baseInterpreter -Parent),(Join-Path $baseRoot 'DLLs'),$root,$env:SystemRoot,(Join-Path $env:SystemRoot 'System32'))) { $nativeRoots.Add([IO.Path]::GetFullPath($path)) }
    foreach ($path in @($env:PYTHONPATH -split [IO.Path]::PathSeparator)) {
        if ([string]::IsNullOrEmpty($path)) { if ($env:PYTHONPATH) { throw 'PYTHONPATH contains an empty entry.' }; continue }
        Assert-ApprovedSearchPath $path $Roots $Deadline
        if (-not $pythonPathSeen.Add([IO.Path]::GetFullPath($path))) { throw 'PYTHONPATH contains a duplicate or case-ambiguous entry.' }
        if ($path.Contains('!') -or [IO.Path]::GetExtension($path) -iin @('.zip','.egg','.whl')) { throw "Active PYTHONPATH archive is unsupported: $path" }
        $pythonRoots.Add([IO.Path]::GetFullPath($path))
    }
    foreach ($path in @($env:PATH -split [IO.Path]::PathSeparator)) {
        if ([string]::IsNullOrWhiteSpace($path)) { throw 'PATH contains an empty native search entry.' }
        Assert-ApprovedSearchPath $path $Roots $Deadline
        if (-not $nativePathSeen.Add([IO.Path]::GetFullPath($path))) { throw 'PATH contains a duplicate or case-ambiguous entry.' }
        $nativeRoots.Add([IO.Path]::GetFullPath($path))
    }
    $site = Join-Path $venvRoot 'Lib/site-packages'
    $packageNativeRoots = [Collections.Generic.List[string]]::new()
    foreach ($name in @('numpy.libs','shapely.libs','pyproj.libs')) {
        $tree = Join-Path $site $name
        if (-not (Test-Path -LiteralPath $tree -PathType Container)) { throw "Required native sibling tree is absent: $tree" }
        $packageNativeRoots.Add([IO.Path]::GetFullPath($tree))
    }
    $dataRoots = [Collections.Generic.List[string]]::new()
    $dataRoots.Add([IO.Path]::GetFullPath($site))
    foreach ($name in @('PROJ_DATA','PROJ_LIB','GDAL_DATA')) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) { $dataRoots.Add([IO.Path]::GetFullPath($value)) }
    }
    $stdlibZip = Join-Path $baseRoot 'python313.zip'
    if (Test-Path -LiteralPath $stdlibZip) { throw "Optional standard-library archive is present and unsupported: $stdlibZip" }
    else { $Record.finiteStartupProfileProgress.absentOptionalSources = @($stdlibZip); Save-Caller $Record }
    $Record.finiteStartupProfileProgress.stage = 'enumerate-python-and-native-candidates'
    Save-Caller $Record
    $visited = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $directorySpellings = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $scanState = [pscustomobject]@{ candidateCount = 0; bytesHashed = [long]0; directoryCount = 0 }
    $pythonSuffixes = @('.py','.pyw','.pyc','.pyo','.pyd')
    $nativeSuffixes = @('.pyd','.dll','.exe','.ocx','.cpl')
    $archiveSuffixes = @('.zip','.egg','.whl')
    $classifyFile = {
        param([string]$Path,[bool]$PythonRole,[bool]$AllFilesRole)
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline before finite-profile file classification.' }
        Assert-NoReparsePath $Path
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Finite-profile path is not a regular file: $Path" }
        $before = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if ($before.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Finite-profile file is a reparse point: $Path" }
        $stream = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        try {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline before finite-profile header read.' }
            $header = New-Object byte[] 2
            $read = $stream.Read($header,0,2)
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after finite-profile header read.' }
            $hasMz = $read -eq 2 -and $header[0] -eq 0x4d -and $header[1] -eq 0x5a
        }
        finally { $stream.Dispose() }
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after finite-profile header metadata check.' }
        $after = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after finite-profile header identity check.' }
        if ($before.Length -ne $after.Length -or $before.LastWriteTimeUtc -ne $after.LastWriteTimeUtc) { throw "Finite-profile file changed during header observation: $Path" }
        $extension = [IO.Path]::GetExtension($Path).ToLowerInvariant()
        $isNative = $extension -in $nativeSuffixes -or $hasMz
        $isPassiveArchive = $extension -in $archiveSuffixes -and -not $isNative
        $isCandidate = $AllFilesRole -or $isNative -or ($PythonRole -and $extension -in $pythonSuffixes)
        return @{ isNative = $isNative; isPassiveArchive = $isPassiveArchive; isCandidate = $isCandidate }
    }
    $assertNativeSidecars = {
        param([string]$Path)
        foreach ($suffix in @('.local','.manifest','.config')) {
            foreach ($sidecar in @($Path + $suffix,[IO.Path]::ChangeExtension($Path,$suffix))) {
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during finite-profile sidecar check.' }
                $exists = $false
                try { $null = [IO.File]::GetAttributes($sidecar); $exists = $true }
                catch [IO.FileNotFoundException] { $exists = $false }
                catch [IO.DirectoryNotFoundException] { $exists = $false }
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after finite-profile sidecar check.' }
                if ($exists) { throw "Unresolved loader redirection sidecar: $sidecar" }
            }
        }
    }
    $scan = {
        param([string]$ScanRoot,[bool]$Recursive,[bool]$PythonFiles,[bool]$AllFiles,[bool]$LoaderRelevant)
        if (-not (Test-Path -LiteralPath $ScanRoot -PathType Container)) { throw "Required finite-profile directory is absent: $ScanRoot" }
        Assert-NoReparsePath $ScanRoot
        $pending = [Collections.Generic.Stack[string]]::new(); $pending.Push($ScanRoot)
        while ($pending.Count -gt 0) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline during finite-profile directory scan: $ScanRoot" }
            $current = [IO.Path]::GetFullPath($pending.Pop())
            $directoryKey = $current.ToLowerInvariant()
            if ($directorySpellings.ContainsKey($directoryKey) -and $directorySpellings[$directoryKey] -cne $current) { throw "Finite-profile directory case collision: $($directorySpellings[$directoryKey]) <> $current" }
            $directorySpellings[$directoryKey] = $current
            $scanState.directoryCount = [int]$scanState.directoryCount + 1
            $Record.finiteStartupProfileProgress.directoryCount = $scanState.directoryCount
            if (($scanState.directoryCount % 64) -eq 0) { Save-Caller $Record }
            foreach ($item in Get-ChildItem -LiteralPath $current -Force -ErrorAction Stop) {
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during finite-profile entry enumeration.' }
                if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Finite-profile path is a reparse point: $($item.FullName)" }
                $nameFolded = $item.Name.ToLowerInvariant()
                $customization = $nameFolded -in @('sitecustomize','usercustomize') -or $nameFolded.StartsWith('sitecustomize.') -or $nameFolded.StartsWith('usercustomize.')
                if ($item.PSIsContainer) {
                    if ($customization) { throw "Python customization package is unsupported: $($item.FullName)" }
                    if ($LoaderRelevant -and ($nameFolded.EndsWith('.local') -or $nameFolded.EndsWith('.manifest') -or $nameFolded.EndsWith('.config'))) { throw "Unresolved loader redirection directory: $($item.FullName)" }
                    if ($Recursive) { $pending.Push($item.FullName) }
                    continue
                }
                $exactPath = [IO.Path]::GetFullPath($item.FullName)
                $classification = & $classifyFile $exactPath $PythonFiles $AllFiles
                if ($customization -or $item.BaseName.ToLowerInvariant() -in @('sitecustomize','usercustomize') -or $item.BaseName.ToLowerInvariant().StartsWith('sitecustomize.') -or $item.BaseName.ToLowerInvariant().StartsWith('usercustomize.')) { throw "Python customization module is unsupported: $($item.FullName)" }
                if ($LoaderRelevant -and ($nameFolded.EndsWith('.local') -or $nameFolded.EndsWith('.manifest') -or $nameFolded.EndsWith('.config'))) { throw "Unresolved loader redirection sidecar: $($item.FullName)" }
                if ($classification.isNative) { & $assertNativeSidecars $exactPath }
                if ($classification.isCandidate) {
                    $candidateKey = $exactPath.ToLowerInvariant()
                    if ($visited.ContainsKey($candidateKey)) {
                        if ($visited[$candidateKey] -cne $exactPath) { throw "Finite-profile candidate case collision: $($visited[$candidateKey]) <> $exactPath" }
                        continue
                    }
                    Assert-FrozenProfileCandidate $item.FullName $RepoMap $ExternalMap $Deadline
                    $visited[$candidateKey] = $exactPath
                    $scanState.candidateCount = [int]$scanState.candidateCount + 1
                    $scanState.bytesHashed = [long]$scanState.bytesHashed + [long]$item.Length
                    $Record.finiteStartupProfileProgress.candidateCount = $scanState.candidateCount
                    $Record.finiteStartupProfileProgress.bytesHashed = $scanState.bytesHashed
                    if (($scanState.candidateCount % 32) -eq 0) { Save-Caller $Record }
                }
            }
        }
    }
    try {
        foreach ($path in $pythonRoots | Select-Object -Unique) { & $scan $path $true $true $false $false }
        foreach ($path in $nativeRoots | Select-Object -Unique) { & $scan $path $false $false $false $true }
        foreach ($path in $packageNativeRoots | Select-Object -Unique) { & $scan $path $true $false $false $true }
        foreach ($path in $dataRoots | Select-Object -Unique) { & $scan $path $true $false $true $false }
    }
    finally {
        $Record.finiteStartupProfileProgress.candidateCount = $scanState.candidateCount
        $Record.finiteStartupProfileProgress.bytesHashed = $scanState.bytesHashed
        $Record.finiteStartupProfileProgress.directoryCount = $scanState.directoryCount
        Save-Caller $Record
    }
    $Record.finiteStartupProfileProgress.stage = 'reconcile-frozen-candidate-set'
    Save-Caller $Record
    $expectedCandidates = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $candidateBindings = @()
    foreach ($binding in $RepoMap.Values) { $candidateBindings += ,@{ path = [IO.Path]::GetFullPath((Join-Path $root ([string]$binding.path).Replace('/','\'))); item = $binding } }
    foreach ($binding in $ExternalMap.Values) { $candidateBindings += ,@{ path = [IO.Path]::GetFullPath([string]$binding.path); item = $binding } }
    foreach ($binding in $candidateBindings) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while reconciling frozen finite-profile candidates.' }
        $full = [string]$binding.path
        $inPython = $false
        foreach ($directory in $pythonRoots) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline deriving Python role for frozen candidate.' }
            $prefix = ([IO.Path]::GetFullPath($directory).TrimEnd('\') + '\')
            if ($full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { $inPython = $true; break }
        }
        $inNative = $false
        foreach ($directory in $nativeRoots) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline deriving native role for frozen candidate.' }
            if ([IO.Path]::GetDirectoryName($full).Equals([IO.Path]::GetFullPath($directory).TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase)) { $inNative = $true; break }
        }
        if (-not $inNative) {
            foreach ($directory in $packageNativeRoots) {
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline deriving package-native role for frozen candidate.' }
                $prefix = ([IO.Path]::GetFullPath($directory).TrimEnd('\') + '\')
                if ($full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { $inNative = $true; break }
            }
        }
        $inData = $false
        foreach ($directory in $dataRoots) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline deriving data role for frozen candidate.' }
            $prefix = ([IO.Path]::GetFullPath($directory).TrimEnd('\') + '\')
            if ($full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { $inData = $true; break }
        }
        if (-not ($inPython -or $inNative -or $inData)) { continue }
        $classification = & $classifyFile $full $inPython $inData
        $fileName = [IO.Path]::GetFileName($full).ToLowerInvariant()
        if ($inNative -and ($fileName.EndsWith('.local') -or $fileName.EndsWith('.manifest') -or $fileName.EndsWith('.config'))) { throw "Unresolved loader redirection sidecar: $full" }
        if ($classification.isNative) { & $assertNativeSidecars $full }
        if ($classification.isCandidate) {
            [void]$expectedCandidates.Add($full)
            $key = $full.ToLowerInvariant()
            if (-not $visited.ContainsKey($key)) { throw "Frozen candidate entry was not observed in finite profile: $full" }
            if ($visited[$key] -cne $full) { throw "Frozen candidate identity has a case collision: $($visited[$key]) <> $full" }
        }
    }
    if ($expectedCandidates.Count -ne $visited.Count) { throw 'Discovered and frozen finite-profile candidate sets do not reconcile.' }
    $Record.finiteStartupProfileProgress.stage = 'complete'
    $Record.finiteStartupProfileProgress.candidateCount = $scanState.candidateCount
    $Record.finiteStartupProfileProgress.bytesHashed = $scanState.bytesHashed
    Save-Caller $Record
    if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Finite startup profile expired before final success check.' }
    return @{ passes = $true; candidateCount = $scanState.candidateCount; bytesHashed = $scanState.bytesHashed; directoryCount = $scanState.directoryCount; profile = 'finite-trusted-startup-v1'; atomicLoadConfinement = $false }
}

function Test-StandaloneFrozenClosure([string]$InputManifestPath, [string]$ExternalManifestPath, [string]$RuntimeIdentityPath, [long]$Deadline, [hashtable]$Record) {
    $Record.standaloneFrozenClosureProgress = @{ stage = 'hash-control-files'; repositoryCheckedCount = 0; externalCheckedCount = 0 }
    Save-Caller $Record
    $inputHash = Get-FileSha256BeforeDeadline $InputManifestPath $Deadline
    $externalHash = Get-FileSha256BeforeDeadline $ExternalManifestPath $Deadline
    $identityHash = Get-FileSha256BeforeDeadline $RuntimeIdentityPath $Deadline
    $manifest = Get-JsonObjectBeforeDeadline $InputManifestPath $Deadline
    $external = Get-JsonObjectBeforeDeadline $ExternalManifestPath $Deadline
    $identity = Get-JsonObjectBeforeDeadline $RuntimeIdentityPath $Deadline
    $Record.standaloneFrozenClosureProgress.stage = 'validate-control-schemas'
    Save-Caller $Record
    if ($manifest.schema -ne 'teignmouth-float32-build-input-v1' -or
        $manifest.issueId -ne 'Teignmouth-float32-topology-representation-1' -or
        $manifest.buildOrdinal -ne 3 -or $manifest.candidateEligibleForServing -ne $false -or
        $manifest.files -isnot [array] -or $manifest.files.Count -lt 291 -or
        $manifest.fileCount -ne $manifest.files.Count) { throw 'Standalone input manifest controls are invalid.' }
    if ($external.schema -ne 'teignmouth-build3-external-runtime-v1' -or
        $external.roots -isnot [array] -or $external.roots.Count -eq 0 -or
        $external.entries -isnot [array] -or $external.entries.Count -eq 0 -or
        $external.rootCount -ne $external.roots.Count -or
        $external.entryCount -ne $external.entries.Count) { throw 'External runtime manifest controls are invalid.' }
    if ($identity.schema -ne 'teignmouth-build3-runtime-identity-v1' -or
        $identity.identity -isnot [System.Collections.IDictionary] -or
        $identity.externalRuntimeManifestSha256 -ne $externalHash) { throw 'Runtime identity schema/linkage is invalid.' }

    $rootPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $approvedCategories = @('venv-runtime', 'base-python-runtime', 'windows-system-runtime')
    foreach ($rootRecord in $external.roots) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while validating external roots.' }
        if ($rootRecord -isnot [System.Collections.IDictionary] -or
            $rootRecord.category -notin $approvedCategories -or
            [string]::IsNullOrWhiteSpace([string]$rootRecord.path)) { throw 'Malformed or unapproved external root.' }
        $rootPath = [IO.Path]::GetFullPath([string]$rootRecord.path)
        if ($rootPath -ne [string]$rootRecord.path) { throw "External root is noncanonical: $rootPath" }
        Assert-LocalCanonicalPath $rootPath
        Assert-NoReparsePath $rootPath
        if (-not (Test-Path -LiteralPath $rootPath -PathType Container) -or
            -not $rootPaths.Add($rootPath)) { throw "External root is unavailable or duplicated: $rootPath" }
    }
    $Record.standaloneFrozenClosureProgress.stage = 'verify-repository-references'
    Save-Caller $Record

    $repoPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $repoMap = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $repoFoldedPaths = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $required = @(
        'pipeline/scripts/invoke_teignmouth_float32_build3.ps1',
        'pipeline/scripts/run_teignmouth_float32_build3.py',
        'pipeline/scripts/teignmouth_build3_runtime_preflight.py',
        'pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py',
        'pipeline/scripts/build_teignmouth_float32_candidate.py',
        'pipeline/torquay_pipeline/road_surface.py',
        'pipeline/torquay_pipeline/road_surface_float32_frame.py',
        'pipeline/torquay_pipeline/road_surface_topology.py',
        'pipeline/torquay_pipeline/teignmouth_corridor_continuation.py',
        'pipeline/torquay_pipeline/teignmouth_corridor_prototype.py',
        'pipeline/torquay_pipeline/teignmouth_float32_candidate.py',
        'pipeline/.venv/Scripts/python.exe',
        'pipeline/.venv/pyvenv.cfg',
        'config/road-surface-teignmouth-float32.json',
        'docs/milestones/artifacts/Teignmouth-float32-topology/build-3/external-runtime-manifest.json',
        'docs/milestones/artifacts/Teignmouth-float32-topology/build-3/runtime-identity.json'
    )
    foreach ($binding in $manifest.files) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while validating repository closure.' }
        if ($binding -isnot [System.Collections.IDictionary]) { throw 'Malformed repository binding.' }
        $relative = [string]$binding.path
        if (-not [string]::IsNullOrWhiteSpace($relative)) {
            if ($repoFoldedPaths.ContainsKey($relative) -and $repoFoldedPaths[$relative] -cne $relative) { throw "Repository bindings have case-distinct references: $($repoFoldedPaths[$relative]) <> $relative" }
            $repoFoldedPaths[$relative] = $relative
        }
        if ([string]::IsNullOrWhiteSpace($relative) -or $relative.Contains('\') -or
            [IO.Path]::IsPathRooted($relative) -or $relative.Split('/').Contains('..') -or
            -not $repoPaths.Add($relative) -or -not $binding.Contains('byteLength') -or
            -not $binding.Contains('sha256') -or [long]$binding.byteLength -lt 0 -or
            [string]$binding.sha256 -notmatch '^[0-9a-f]{64}$') { throw "Invalid or duplicate repository binding: $relative" }
        $full = [IO.Path]::GetFullPath((Join-Path $root $relative))
        if (-not $full.StartsWith(([IO.Path]::GetFullPath($root).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
            throw "Repository binding escapes fixed root: $relative"
        }
        Assert-NoReparsePath $full
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Repository binding is unavailable: $relative" }
        $info = Get-Item -LiteralPath $full
        $sha = Get-FileSha256BeforeDeadline $full $Deadline
        if ($info.Length -ne [long]$binding.byteLength -or $sha -ne [string]$binding.sha256) {
            throw "Repository binding size/hash mismatch: $relative"
        }
        $repoMap.Add($relative, $binding)
        $Record.standaloneFrozenClosureProgress.repositoryCheckedCount = $repoMap.Count
        if (($repoMap.Count % 16) -eq 0) { Save-Caller $Record }
    }
    foreach ($requiredPath in $required) {
        if (-not $repoMap.ContainsKey($requiredPath)) { throw "Mandatory repository control is unbound: $requiredPath" }
    }
    if ($Mode -eq 'build' -and -not $repoMap.ContainsKey('docs/milestones/artifacts/Teignmouth-float32-topology/build-3/reserved-ledger-snapshot.json')) {
        throw 'Mandatory reserved ledger snapshot is unbound.'
    }

    $externalPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $externalMap = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
    $Record.standaloneFrozenClosureProgress.stage = 'verify-external-references'
    Save-Caller $Record
    foreach ($entry in $external.entries) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while validating external runtime closure.' }
        if ($entry -isnot [System.Collections.IDictionary] -or
            [string]::IsNullOrWhiteSpace([string]$entry.path) -or
            -not $entry.Contains('byteLength') -or -not $entry.Contains('sha256') -or
            [long]$entry.byteLength -lt 0 -or [string]$entry.sha256 -notmatch '^[0-9a-f]{64}$' -or
            -not $externalPaths.Add([string]$entry.path)) { throw 'Malformed or duplicate external runtime binding.' }
        $full = [IO.Path]::GetFullPath([string]$entry.path)
        $category = Assert-ExternalPathBound $full $external.roots
        if ($category -ne [string]$entry.category) { throw "External runtime category mismatch: $full" }
        Assert-NoReparsePath $full
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "External runtime file is unavailable: $full" }
        $info = Get-Item -LiteralPath $full
        $sha = Get-FileSha256BeforeDeadline $full $Deadline
        if ($info.Length -ne [long]$entry.byteLength -or $sha -ne [string]$entry.sha256) {
            throw "External runtime binding size/hash mismatch: $full"
        }
        $externalMap.Add($full, $entry)
        $Record.standaloneFrozenClosureProgress.externalCheckedCount = $externalMap.Count
        if (($externalMap.Count % 16) -eq 0) { Save-Caller $Record }
    }
    $canonicalInputPaths = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($relative in $repoMap.Keys) {
        $absolute = [IO.Path]::GetFullPath((Join-Path $root $relative.Replace('/','\')))
        if ($canonicalInputPaths.ContainsKey($absolute)) { throw "Repository bindings share a canonical identity: $($canonicalInputPaths[$absolute]) <> $absolute" }
        $canonicalInputPaths[$absolute] = $absolute
    }
    foreach ($absolute in $externalMap.Keys) {
        $full = [IO.Path]::GetFullPath([string]$absolute)
        if ($canonicalInputPaths.ContainsKey($full) -and $canonicalInputPaths[$full] -cne $full) { throw "Frozen references have case-distinct canonical identities: $($canonicalInputPaths[$full]) <> $full" }
        if ($canonicalInputPaths.ContainsKey($full)) { throw "Repository and external bindings refer to the same canonical file: $full" }
        $canonicalInputPaths[$full] = $full
    }

    foreach ($environmentName in @('PROJ_DATA','PROJ_LIB','GDAL_DATA','GEOS_LIBRARY_PATH','PYTHONPATH','PATH')) {
        $environmentValue = [Environment]::GetEnvironmentVariable($environmentName)
        if ([string]::IsNullOrWhiteSpace($environmentValue)) { continue }
        foreach ($configuredPath in $environmentValue.Split([IO.Path]::PathSeparator)) {
            if ([string]::IsNullOrWhiteSpace($configuredPath)) {
                if ($environmentName -in @('PYTHONPATH','PATH')) { throw "$environmentName contains an empty search entry." }
                continue
            }
            if ((Get-SafeQpcValue) -ge $Deadline) { throw "Deadline checking $environmentName." }
            Assert-ApprovedSearchPath $configuredPath $external.roots $Deadline
        }
    }
    $Record.standaloneFrozenClosureProgress.stage = 'verify-startup-paths'
    Save-Caller $Record
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHONHOME)) {
        Assert-ApprovedSearchPath $env:PYTHONHOME $external.roots $Deadline
    }

    $basePythonRoot = Split-Path $baseInterpreter -Parent
    $pyvenvCfgPath = Join-Path $root 'pipeline/.venv/pyvenv.cfg'
    $pyvenvPolicy = Get-PyvenvPolicy $pyvenvCfgPath $Deadline
    $configuredHome = [IO.Path]::GetFullPath($pyvenvPolicy['home'])
    if ($configuredHome -ne [IO.Path]::GetFullPath($basePythonRoot)) {
        throw 'pyvenv.cfg base home does not match the authenticated base interpreter.'
    }
    $siteDirectories = @(
        (Join-Path $root 'pipeline/.venv/Lib/site-packages'),
        (Join-Path $basePythonRoot 'Lib'),
        (Join-Path $basePythonRoot 'Lib/site-packages')
    )
    $literalPythonRoots = [Collections.Generic.List[string]]::new()
    $literalPythonRootSpellings = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($siteDirectory in $siteDirectories | Select-Object -Unique) {
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while validating Python startup paths.' }
        if (-not (Test-Path -LiteralPath $siteDirectory -PathType Container)) { continue }
        Assert-NoReparsePath $siteDirectory
        foreach ($startupFile in Get-ChildItem -LiteralPath $siteDirectory -File -Force) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while enumerating Python startup files.' }
            if ($startupFile.Extension -eq '.pth' -or $startupFile.Name -in @('sitecustomize.py','usercustomize.py')) {
                $relative = [IO.Path]::GetRelativePath($root, $startupFile.FullName).Replace('\','/')
                $startupPath = [IO.Path]::GetFullPath($startupFile.FullName)
                if (-not $repoMap.ContainsKey($relative) -and -not $externalMap.ContainsKey($startupPath)) {
                    throw "Python startup hook is not frozen-bound: $relative"
                }
                if ($startupFile.Extension -eq '.pth') {
                    $startupBytes = [IO.File]::ReadAllBytes($startupFile.FullName)
                    if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline after reading Python path hook.' }
                    if ($startupBytes | Where-Object { $_ -gt 127 }) { throw "Non-ASCII .pth file is unsupported: $relative" }
                    foreach ($line in Get-Content -LiteralPath $startupFile.FullName) {
                        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline reading Python path hook.' }
                        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
                        if ($line[0] -match '\s') { throw "Leading whitespace in .pth startup hook is unsupported: $relative" }
                        if ($line -match '^import[\t ]') { throw "Executable .pth startup hook is not statically closed: $relative" }
                        $pathLine = $line.TrimEnd()
                        if ($pathLine.Length -gt 0) {
                            $pathTarget = if ([IO.Path]::IsPathRooted($pathLine)) {
                                [IO.Path]::GetFullPath($pathLine)
                            } else {
                                [IO.Path]::GetFullPath((Join-Path $siteDirectory $pathLine))
                            }
                            Assert-ApprovedSearchPath $pathTarget $external.roots $Deadline
                            if (-not (Test-Path -LiteralPath $pathTarget -PathType Container)) { throw "Literal .pth target is not an import directory: $pathTarget" }
                            if ($literalPythonRootSpellings.ContainsKey($pathTarget)) {
                                if ($literalPythonRootSpellings[$pathTarget] -cne $pathTarget) { throw "Literal .pth targets have case-distinct identities: $($literalPythonRootSpellings[$pathTarget]) <> $pathTarget" }
                            } else {
                                $literalPythonRootSpellings.Add($pathTarget,$pathTarget)
                                $literalPythonRoots.Add($pathTarget)
                            }
                        }
                    }
                }
            }
        }
    }
    $profile = Test-FiniteStartupProfile $ExternalManifestPath $RuntimeIdentityPath $Deadline $Record $repoMap $externalMap $external.roots $literalPythonRoots
    $Record.finiteStartupProfileBeforeLaunch = $profile
    Save-Caller $Record
    $Record.standaloneFrozenClosureProgress.stage = 'rehash-control-files'
    Save-Caller $Record
    if ((Get-FileSha256BeforeDeadline $InputManifestPath $Deadline) -ne $inputHash -or
        (Get-FileSha256BeforeDeadline $ExternalManifestPath $Deadline) -ne $externalHash -or
        (Get-FileSha256BeforeDeadline $RuntimeIdentityPath $Deadline) -ne $identityHash) {
        throw 'Frozen runtime manifests changed during standalone prelaunch validation.'
    }
    $Record.standaloneFrozenClosureProgress.stage = 'complete'
    Save-Caller $Record
    return @{
        passes = $true; inputManifestSha256 = $inputHash; externalRuntimeManifestSha256 = $externalHash
        runtimeIdentitySha256 = $identityHash; repositoryCheckedCount = $repoMap.Count
        repositoryDeclaredCount = $manifest.files.Count; externalCheckedCount = $externalPaths.Count
        externalDeclaredCount = $external.entries.Count
    }
}

function Get-NativeIdentity([uint32]$ProcessId, [long]$Deadline = $deadlineQpc) {
    if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline before native process identity query.' }
    $handle = [TeignmouthBuild3Native]::OpenProcess(0x1000 -bor 0x0400, $false, $ProcessId)
    if ($handle -eq [IntPtr]::Zero) { throw "OpenProcess failed for PID $ProcessId." }
    try {
        $pathBuffer = New-Object Text.StringBuilder 32768
        $pathLength = [uint32]$pathBuffer.Capacity
        if (-not [TeignmouthBuild3Native]::QueryFullProcessImageName(
            $handle, 0, $pathBuffer, [ref]$pathLength
        )) { throw "Cannot read native image for PID $ProcessId." }
        $created = [long]0; $exited = [long]0; $kernelTime = [long]0; $userTime = [long]0
        if (-not [TeignmouthBuild3Native]::GetProcessTimes(
            $handle, [ref]$created, [ref]$exited, [ref]$kernelTime, [ref]$userTime
        )) { throw "Cannot read process creation identity for PID $ProcessId." }
        $imageHash = (Get-FileHash -LiteralPath $pathBuffer.ToString() -Algorithm SHA256).Hash.ToLowerInvariant()
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during native image hashing.' }
        return @{
            pid = [uint32]$ProcessId
            creationFileTime = $created
            imagePath = [IO.Path]::GetFullPath($pathBuffer.ToString())
            imageSha256 = $imageHash
        }
    }
    finally {
        [void][TeignmouthBuild3Native]::CloseHandle($handle)
    }
}

function Get-DescendantProcessIds {
    param([uint32[]]$RootIds, [long]$Deadline, [hashtable]$Observation = $null)
    $snapshotStart = $null
    if ($null -ne $Observation) {
        try { $snapshotStart = Get-SafeQpcValue }
        catch { try { $Observation.snapshotClockStatus = 'unavailable' } catch { } }
    }
    $terminalError = [int]-1
    if ($null -ne $Observation) {
        $rows = [TeignmouthBuild3Native]::GetProcessRows($Deadline, [ref]$terminalError)
    } else {
        $rows = [TeignmouthBuild3Native]::GetProcessRows($Deadline)
    }
    $snapshotEnd = $null
    if ($rows.Count -gt 65536) { throw 'Process ancestry snapshot exceeds fixed bound.' }
    if ($null -ne $Observation) {
        try { $snapshotEnd = Get-SafeQpcValue }
        catch { try { $Observation.snapshotClockStatus = 'unavailable' } catch { } }
        $rootsReady = $false
        try {
            $boundedRoots = [uint32[]]::new([Math]::Min(2,$RootIds.Count))
            for ($rootIndex = 0; $rootIndex -lt $boundedRoots.Length; $rootIndex++) { $boundedRoots[$rootIndex] = [uint32]$RootIds[$rootIndex] }
            $Observation.roots = $boundedRoots
            $Observation.rootsCapped = $RootIds.Count -gt 2
            $Observation.snapshotRowCount = [int]$rows.Count
            $Observation.snapshotTerminalError = [int]$terminalError
            $Observation.snapshotStartQpc = if ($null -ne $snapshotStart) { [long]$snapshotStart } else { $null }
            $Observation.snapshotEndQpc = if ($null -ne $snapshotEnd) { [long]$snapshotEnd } else { $null }
            $rootsReady = $true
        } catch { try { $Observation.bookkeepingReady = $false } catch { } }
        try {
            $rowIndexByPid = [Collections.Generic.Dictionary[uint32,int]]::new()
            $duplicatePids = [Collections.Generic.HashSet[uint32]]::new()
            for ($rowIndex = 0; $rowIndex -lt $rows.Count; $rowIndex++) {
                if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during descendant diagnostic bookkeeping.' }
                $rowPid = [uint32]$rows[$rowIndex].processId
                if ($rowIndexByPid.ContainsKey($rowPid)) { [void]$duplicatePids.Add($rowPid) }
                else { $rowIndexByPid.Add($rowPid, [int]$rowIndex) }
            }
            $Observation.rows = $rows
            $Observation.rowIndexByPid = $rowIndexByPid
            $Observation.duplicatePids = $duplicatePids
            $Observation.snapshotStatus = if ($terminalError -eq 18) { 'partial' } elseif ($terminalError -ge 0) { 'unverified-terminal-error' } else { 'unavailable' }
            $Observation.snapshotDuplicatePidAmbiguity = $duplicatePids.Count -gt 0
            $Observation.firstDiscovery = [Collections.Generic.Dictionary[uint32,object]]::new()
            $Observation.bookkeepingReady = $rootsReady
        } catch {
            try { $Observation.bookkeepingReady = $false; $Observation.snapshotStatus = 'unavailable'; $Observation.snapshotBookkeepingStatus = 'unavailable' } catch { }
        }
    }
    $known = [Collections.Generic.HashSet[uint32]]::new()
    foreach ($id in $RootIds) { [void]$known.Add([uint32]$id) }
    $descendants = [Collections.Generic.HashSet[uint32]]::new()
    $passes = 0
    for ($pass = 0; $pass -lt 64; $pass++) {
        $passes = $pass + 1
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during descendant ancestry expansion.' }
        $changed = $false
        if ($null -ne $Observation) { $rowIndex = 0 }
        foreach ($row in $rows) {
            if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline during descendant ancestry census.' }
            if ($known.Contains([uint32]$row.parentPid) -and
                -not $known.Contains([uint32]$row.processId)) {
                [void]$known.Add([uint32]$row.processId)
                [void]$descendants.Add([uint32]$row.processId)
                if ($null -ne $Observation -and $Observation.bookkeepingReady) {
                    try {
                        $Observation.firstDiscovery[[uint32]$row.processId] = [pscustomobject]@{
                            parentPid = [uint32]$row.parentPid; rowIndex = [int]$rowIndex
                        }
                    } catch {
                        try { $Observation.bookkeepingReady = $false; $Observation.snapshotBookkeepingStatus = 'partial' } catch { }
                    }
                }
                $changed = $true
            }
            if ($null -ne $Observation) { $rowIndex++ }
        }
        if (-not $changed) {
            if ($null -ne $Observation) {
                $expansionObservedBeforeDeadline = $false
                if ($Observation.bookkeepingReady) {
                    try { $expansionObservedBeforeDeadline = (Get-SafeQpcValue) -lt $Deadline } catch { }
                }
                try {
                    $Observation.expansionPasses = [int]$passes
                    $Observation.expansionConverged = $true
                    $Observation.expansionComplete = $expansionObservedBeforeDeadline
                    if (-not $Observation.bookkeepingReady) { $Observation.snapshotStatus = 'unavailable' }
                    elseif ($Observation.snapshotTerminalError -eq 18 -and $null -ne $Observation.snapshotStartQpc -and $null -ne $Observation.snapshotEndQpc -and $expansionObservedBeforeDeadline) { $Observation.snapshotStatus = 'complete' }
                    elseif ($Observation.snapshotTerminalError -eq 18) { $Observation.snapshotStatus = 'late' }
                    elseif ($Observation.snapshotTerminalError -ge 0) { $Observation.snapshotStatus = 'unverified-terminal-error' }
                    else { $Observation.snapshotStatus = 'partial' }
                } catch { }
            }
            return @($descendants)
        }
    }
    if ($null -ne $Observation) {
        try {
            $Observation.expansionPasses = [int]$passes
            $Observation.expansionConverged = $false
            $Observation.expansionComplete = $false
        } catch { }
    }
    throw 'Process ancestry exceeded 64 fixed descendant levels.'
}

function Test-DiagnosticCaptureTime([hashtable]$Observation) {
    try { return (Get-SafeQpcValue) -lt [long]$Observation.capture.cutoffQpc }
    catch { $Observation.captureLate = $true; return $false }
}

function Set-DiagnosticChain([hashtable]$Observation, [uint32]$TargetPid) {
    try {
        if (-not (Test-DiagnosticCaptureTime $Observation)) { $Observation.chainStatus = 'late'; return }
        $Observation.chainStatus = 'unavailable'
        $Observation.chain = @()
        $Observation.chainEdgeCountObserved = 0
        $Observation.chainEdgesStored = 0
        $Observation.chainComplete = $false
        $Observation.chainCapped = $false
        $Observation.chainAmbiguous = $false
        $Observation.chainTerminalRoot = $null
        $reverse = [Collections.Generic.List[object]]::new()
        $seen = [Collections.Generic.HashSet[uint32]]::new()
        $current = [uint32]$TargetPid
        $rootSet = [Collections.Generic.HashSet[uint32]]::new()
        foreach ($rootId in $Observation.roots) { [void]$rootSet.Add([uint32]$rootId) }
        $complete = $false
        $late = $false
        while ($Observation.firstDiscovery.ContainsKey($current) -and $reverse.Count -lt 64) {
            if (-not (Test-DiagnosticCaptureTime $Observation)) { $late = $true; break }
            if (-not $seen.Add($current)) { $Observation.chainStatus = 'partial-cycle'; return }
            $edge = $Observation.firstDiscovery[$current]
            $rowIndex = [int]$edge.rowIndex
            if ($rowIndex -lt 0 -or $rowIndex -ge $Observation.rows.Count) { $Observation.chainStatus = 'partial-invalid-row'; return }
            $reverse.Add([pscustomobject]@{ pid = [uint32]$current; parentPid = [uint32]$edge.parentPid; rowIndex = $rowIndex })
            if ($Observation.duplicatePids.Contains([uint32]$current)) { $Observation.chainAmbiguous = $true }
            if ($Observation.duplicatePids.Contains([uint32]$edge.parentPid)) { $Observation.chainAmbiguous = $true }
            $current = [uint32]$edge.parentPid
            if ($rootSet.Contains($current)) { $complete = $true; break }
        }
        $capped = $reverse.Count -eq 64 -and -not $complete -and $Observation.firstDiscovery.ContainsKey($current)
        if (-not (Test-DiagnosticCaptureTime $Observation)) {
            $Observation.chainEdgeCountObserved = [int]$reverse.Count
            $Observation.chainEdgesStored = 0
            $Observation.chain = $null
            $Observation.chainCapped = [bool]$capped
            $Observation.chainComplete = $false
            $Observation.chainTerminalRoot = $null
            $Observation.chainStatus = 'late'
            return
        }
        $edges = [object[]]::new($reverse.Count)
        for ($edgeIndex = 0; $edgeIndex -lt $reverse.Count; $edgeIndex++) {
            if (-not (Test-DiagnosticCaptureTime $Observation)) { $late = $true; break }
            $edges[$edgeIndex] = $reverse[$reverse.Count - 1 - $edgeIndex]
        }
        if ($late -or -not (Test-DiagnosticCaptureTime $Observation)) {
            $Observation.chainEdgeCountObserved = [int]$reverse.Count
            $Observation.chainEdgesStored = 0
            $Observation.chain = $null
            $Observation.chainCapped = [bool]$capped
            $Observation.chainComplete = $false
            $Observation.chainTerminalRoot = $null
            $Observation.chainStatus = 'late'
            return
        }
        $Observation.chainEdgeCountObserved = [int]$reverse.Count
        $Observation.chainEdgesStored = [int]$edges.Length
        $Observation.chain = $edges
        $Observation.chainCapped = [bool]$capped
        $snapshotComplete = $Observation.snapshotStatus -eq 'complete' -and [bool]$Observation.expansionComplete
        $Observation.chainComplete = $complete -and $snapshotComplete -and -not $capped -and -not $Observation.chainAmbiguous
        $Observation.chainTerminalRoot = if ($Observation.chainComplete) { [uint32]$current } else { $null }
        $Observation.chainStatus = if ($Observation.chainComplete) { 'complete' } elseif ($Observation.chainAmbiguous) { 'ambiguous' } elseif ($capped) { 'capped-root-unknown' } elseif ($Observation.snapshotStatus -eq 'late') { 'late' } else { 'partial' }
    } catch { $Observation.chainStatus = 'unavailable' }
}

function New-FalseMembershipObservation([hashtable]$Snapshot, [uint32]$TargetPid, [IntPtr]$ProcessHandle,
    [object]$MembershipStartQpc, [object]$MembershipEndQpc, [uint32[]]$JobIds, [int]$OriginalJobIdCount) {
    $now = Get-SafeQpcValue
    $reserve = [long][Math]::Ceiling(1.0 * $qpcFrequency)
    $opportunity = [long][Math]::Ceiling(0.020 * $qpcFrequency)
    $firstFalseQpc = [long]$MembershipEndQpc
    $cutoff = [Math]::Min([long]($deadlineQpc - $reserve), [long]($firstFalseQpc + $opportunity))
    $hasCaptureReserve = ($deadlineQpc - $now) -ge $reserve -and $cutoff -gt $now
    if (-not $hasCaptureReserve) {
        return @{
            minimalStatusToken = $true; targetPid = [uint32]$TargetPid; status = 'skipped-no-reserve'
            membershipStartQpc = if ($null -ne $MembershipStartQpc) { [long]$MembershipStartQpc } else { $null }
            membershipStartQpcStatus = if ($null -ne $MembershipStartQpc) { 'observed' } else { 'unavailable' }
            membershipEndQpc = [long]$MembershipEndQpc
        }
    }
    if ((Get-SafeQpcValue) -ge $cutoff) {
        return @{
            minimalStatusToken = $true; targetPid = [uint32]$TargetPid; status = 'skipped-cutoff'
            membershipStartQpc = if ($null -ne $MembershipStartQpc) { [long]$MembershipStartQpc } else { $null }
            membershipStartQpcStatus = if ($null -ne $MembershipStartQpc) { 'observed' } else { 'unavailable' }
            membershipEndQpc = [long]$MembershipEndQpc
        }
    }
    $originalJobIdCount = [int]$OriginalJobIdCount
    $boundedJobIds = [uint32[]]::new([Math]::Min(64,$originalJobIdCount))
    for ($jobIndex = 0; $jobIndex -lt $boundedJobIds.Length; $jobIndex++) { $boundedJobIds[$jobIndex] = [uint32]$JobIds[$jobIndex] }
    $observation = @{
        targetPid = [uint32]$TargetPid; status = 'unavailable'; association = 'snapshot-incarnation-unproven'
        roots = $Snapshot.roots; rootsCapped = [bool]$Snapshot.rootsCapped; cutoffQpc = [long]$cutoff
        jobQuery = @{ startQpc = $Snapshot.jobQueryStartQpc; endQpc = $Snapshot.jobQueryEndQpc; status = 'observed'; ids = $boundedJobIds; idsComplete = $originalJobIdCount -le 64; idsCapped = $originalJobIdCount -gt 64; originalIdCount = $originalJobIdCount }
        snapshot = $null; chain = $null; membership = @{ startQpc = if ($null -ne $MembershipStartQpc) { [long]$MembershipStartQpc } else { $null }; startQpcStatus = if ($null -ne $MembershipStartQpc) { 'observed' } else { 'unavailable' }; endQpc = [long]$MembershipEndQpc; querySucceeded = $true; member = $false; queryError = $null; jobRole = 'outer'; sameRetainedHandle = $true }
        times = @{ status = 'not-queried'; startQpc = $null; endQpc = $null; succeeded = $null; error = $null; creationFileTime = $null; exitFileTime = $null }
        image = @{ status = 'not-queried'; startQpc = $null; endQpc = $null; succeeded = $null; error = $null; reportedLength = $null; rawPath = $null; bufferCharacters = 1024; retried = $false }
        close = @{ attempt = $false; status = 'unconfirmed'; succeeded = $null; error = $null; endQpc = $null }
        capture = @{ absoluteDeadlineQpc = [long]$deadlineQpc; cutoffQpc = [long]$cutoff; firstFalseQpc = [long]$firstFalseQpc; capped = ([bool]$Snapshot.rootsCapped -or $originalJobIdCount -gt 64); late = $false; omitted = $false; additionalFalsePidsNotDetailed = 0 }
        rows = $Snapshot.rows; rowIndexByPid = $Snapshot.rowIndexByPid; duplicatePids = $Snapshot.duplicatePids; firstDiscovery = $Snapshot.firstDiscovery
        snapshotStartQpc = $Snapshot.snapshotStartQpc; snapshotEndQpc = $Snapshot.snapshotEndQpc; snapshotTerminalError = $Snapshot.snapshotTerminalError
        snapshotStatus = $Snapshot.snapshotStatus; snapshotRowCount = $Snapshot.snapshotRowCount; snapshotDuplicatePidAmbiguity = $Snapshot.snapshotDuplicatePidAmbiguity
        expansionPasses = $Snapshot.expansionPasses; expansionConverged = $Snapshot.expansionConverged; expansionComplete = $Snapshot.expansionComplete
        captureLate = $false
    }
    $Observation.capture.capped = $Observation.rootsCapped -or $Observation.jobQuery.idsCapped
    $Observation.status = 'partial'
    try {
        if (-not (Test-DiagnosticCaptureTime $Observation)) { $Observation.chainStatus = 'late'; $Observation.capture.late = $true }
        elseif ($Snapshot.bookkeepingReady -and $null -ne $Snapshot.firstDiscovery) { Set-DiagnosticChain $Observation $TargetPid }
        else { $Observation.chainStatus = 'unavailable' }
        if (Test-DiagnosticCaptureTime $Observation) {
            $created = [long]0; $exited = [long]0; $kernel = [long]0; $user = [long]0
            $Observation.times.startQpc = Get-SafeQpcValue
            $timesOk = [TeignmouthBuild3Native]::GetProcessTimes($ProcessHandle,[ref]$created,[ref]$exited,[ref]$kernel,[ref]$user)
            $timesError = if ($timesOk) { 0 } else { [Runtime.InteropServices.Marshal]::GetLastWin32Error() }
            $Observation.times.endQpc = Get-SafeQpcValue
            if ($Observation.times.endQpc -le $cutoff) {
                $Observation.times.succeeded = [bool]$timesOk; $Observation.times.error = if ($timesOk) { $null } else { [int]$timesError }
                $Observation.times.status = if ($timesOk) { 'observed' } else { 'failed' }
                if ($timesOk) { $Observation.times.creationFileTime = [long]$created; $Observation.times.exitFileTime = [long]$exited }
            } else { $Observation.times.status = 'late'; $Observation.capture.late = $true }
        } else { $Observation.times.status = 'skipped-cutoff' }
        if (Test-DiagnosticCaptureTime $Observation) {
            $buffer = [Text.StringBuilder]::new(1024)
            $length = [uint32]1024
            $Observation.image.startQpc = Get-SafeQpcValue
            $imageOk = [TeignmouthBuild3Native]::QueryFullProcessImageName($ProcessHandle,0,$buffer,[ref]$length)
            $imageError = if ($imageOk) { 0 } else { [Runtime.InteropServices.Marshal]::GetLastWin32Error() }
            $Observation.image.endQpc = Get-SafeQpcValue
            $Observation.image.reportedLength = [uint32]$length
            if ($Observation.image.endQpc -le $cutoff) {
                $Observation.image.succeeded = [bool]$imageOk; $Observation.image.error = if ($imageOk) { $null } else { [int]$imageError }
                if ($imageOk -and $length -le 1024) { $Observation.image.rawPath = $buffer.ToString(0,[int]$length); $Observation.image.status = 'observed' }
                elseif (-not $imageOk -and $imageError -eq 122) { $Observation.image.status = 'insufficient-buffer' }
                elseif ($imageOk) { $Observation.image.status = 'invalid-length' }
                else { $Observation.image.status = 'failed' }
            } else { $Observation.image.status = 'late'; $Observation.capture.late = $true }
        } else { $Observation.image.status = 'skipped-cutoff' }
    } catch { $Observation.capture.omitted = $true; $Observation.status = 'partial' }
    if ($Observation.captureLate) { $Observation.capture.late = $true }
    return $Observation
}

function Convert-FalseMembershipObservation([hashtable]$Observation) {
    try { if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null } }
    catch { return $null }
    if ($Observation.minimalStatusToken) {
        try {
            $minimal = @{
                targetPid = $Observation.targetPid; member = $false; status = $Observation.status
                membershipStartQpc = $Observation.membershipStartQpc
                membershipStartQpcStatus = $Observation.membershipStartQpcStatus
                membershipEndQpc = $Observation.membershipEndQpc; detailsOmitted = $true
                association = 'snapshot-incarnation-unproven'
            }
            $minimalJson = ConvertTo-Json -InputObject $minimal -Compress -Depth 2
            if ([Text.UTF8Encoding]::new($false).GetByteCount($minimalJson) -gt 1024) { return $null }
            if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null }
            return $minimalJson
        } catch { return $null }
    }
    $fallbackRequired = $false
    $json = $null
    try {
        $snapshot = @{
            startQpc = $Observation.snapshotStartQpc; endQpc = $Observation.snapshotEndQpc; status = $Observation.snapshotStatus
            terminalError = $Observation.snapshotTerminalError; rowCount = $Observation.snapshotRowCount
            expansionPasses = $Observation.expansionPasses; converged = $Observation.expansionConverged
            duplicatePidAmbiguity = $Observation.snapshotDuplicatePidAmbiguity
        }
        $chain = @{
            edges = @($Observation.chain); edgeCountObserved = $Observation.chainEdgeCountObserved; edgesStored = $Observation.chainEdgesStored
            complete = $Observation.chainComplete; capped = $Observation.chainCapped; ambiguous = $Observation.chainAmbiguous
            terminalRoot = $Observation.chainTerminalRoot; status = $Observation.chainStatus
        }
        $payload = @{
            targetPid = $Observation.targetPid; status = $Observation.status; association = $Observation.association; roots = @($Observation.roots)
            rootsCapped = $Observation.rootsCapped; jobQuery = $Observation.jobQuery; snapshot = $snapshot; chain = $chain
            membership = $Observation.membership; times = $Observation.times; image = $Observation.image; close = $Observation.close; capture = $Observation.capture
        }
        $json = ConvertTo-Json -InputObject $payload -Compress -Depth 8
    } catch { $fallbackRequired = $true }
    if (-not $fallbackRequired) {
        try { if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null } } catch { return $null }
        try { if ([Text.UTF8Encoding]::new($false).GetByteCount($json) -gt 16384) { $fallbackRequired = $true } }
        catch { $fallbackRequired = $true }
        try { if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null } } catch { return $null }
    }
    if ($fallbackRequired) {
        try {
            if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null }
            $minimal = @{ targetPid = $Observation.targetPid; member = $false; snapshotStatus = $Observation.snapshotStatus; detailsOmitted = $true; reason = 'payload-limit-or-serialization' }
            $fallbackJson = ConvertTo-Json -InputObject $minimal -Compress -Depth 2
            if ([Text.UTF8Encoding]::new($false).GetByteCount($fallbackJson) -gt 1024) { return $null }
            if ((Get-SafeQpcValue) -ge $deadlineQpc) { return $null }
            return $fallbackJson
        } catch { return $null }
    }
    return $json
}

function Assert-OwnedJobTree([IntPtr]$Job, [uint32[]]$RootIds) {
    $diagnosticEnabled = $Mode -eq 'self-check'
    if ($diagnosticEnabled) { try { $script:pendingDescendantDiagnostic = $null } catch { } }
    $jobQueryStart = $null
    $snapshot = $null
    if ($diagnosticEnabled) {
        try { $jobQueryStart = Get-SafeQpcValue } catch { }
        try { $snapshot = @{} } catch { }
    }
    $activeIds = [TeignmouthBuild3Native]::GetJobProcessIds($Job, $deadlineQpc)
    $activeIdCount = [int]$activeIds.Count
    if ($activeIds.Count -gt 65536) { throw 'Owned Job exceeds fixed process-count bound.' }
    $jobQueryEnd = $null
    if ($diagnosticEnabled -and $null -ne $snapshot) {
        try { $jobQueryEnd = Get-SafeQpcValue } catch { }
        try {
            $snapshot.jobQueryStartQpc = $jobQueryStart
            $snapshot.jobQueryEndQpc = $jobQueryEnd
            $snapshot.jobIdCount = $activeIdCount
        } catch { $snapshot = $null }
    }
    $descendantIds = Get-DescendantProcessIds $RootIds $deadlineQpc $snapshot
    $uncontained = [Collections.Generic.List[uint32]]::new()
    $falseMembershipCount = 0
    foreach ($id in $descendantIds) {
        if ((Get-SafeQpcValue) -ge $deadlineQpc) { throw 'Deadline during owned Job membership census.' }
        $process = [TeignmouthBuild3Native]::OpenProcess(0x1000, $false, $id)
        if ($process -eq [IntPtr]::Zero) { continue }
        $membershipObservation = $null
        $membershipFalseCommitted = $false
        try {
            $member = $false
            $membershipStart = $null
            if ($diagnosticEnabled) { try { $membershipStart = Get-SafeQpcValue } catch { } }
            $membershipOk = [TeignmouthBuild3Native]::IsProcessInJob($process, $Job, [ref]$member)
            if (-not $membershipOk) {
                if ($diagnosticEnabled) { try { $membershipQueryError = [Runtime.InteropServices.Marshal]::GetLastWin32Error() } catch { } }
                throw "IsProcessInJob failed for descendant PID $id."
            }
            if (-not $member) {
                $uncontained.Add($id)
                $falseMembershipCount++
                $membershipFalseCommitted = $true
                if ($diagnosticEnabled -and $falseMembershipCount -eq 1) {
                    $membershipEnd = $null
                    if ($null -ne $snapshot) { try { $membershipEnd = Get-SafeQpcValue } catch { } }
                    if ($null -ne $membershipEnd -and $null -ne $snapshot) {
                        try {
                            $membershipObservation = New-FalseMembershipObservation $snapshot ([uint32]$id) $process $membershipStart $membershipEnd $activeIds $activeIdCount
                            $script:pendingDescendantDiagnostic = $membershipObservation
                        } catch { $membershipObservation = $null }
                    }
                } elseif ($diagnosticEnabled -and $null -ne $script:pendingDescendantDiagnostic) {
                    try { $script:pendingDescendantDiagnostic.capture.additionalFalsePidsNotDetailed++ } catch { }
                }
            }
        }
        finally {
            if ($diagnosticEnabled -and $uncontained.Count -gt 0) {
                try {
                    $closeSucceeded = [TeignmouthBuild3Native]::CloseHandle($process)
                    if (-not $closeSucceeded) { $closeError = [Runtime.InteropServices.Marshal]::GetLastWin32Error() }
                } catch { $closeSucceeded = $false; $closeError = -1 }
            } else {
                [void][TeignmouthBuild3Native]::CloseHandle($process)
            }
            if ($diagnosticEnabled -and $null -ne $membershipObservation -and -not $membershipObservation.minimalStatusToken) {
                try {
                    $membershipObservation.close.attempt = $true
                    $membershipObservation.close.succeeded = [bool]$closeSucceeded
                    $membershipObservation.close.error = if ($closeSucceeded) { $null } else { $closeError }
                    $membershipObservation.close.status = if ($closeSucceeded) { 'closed' } else { 'release-unconfirmed' }
                } catch { $membershipObservation.close.status = 'release-unconfirmed' }
            }
        }
    }
    if ($uncontained.Count -gt 0) {
        $rejectionMessage = "Descendants escaped the owned Job Object: $($uncontained -join ',')."
        if ($diagnosticEnabled -and $null -ne $script:pendingDescendantDiagnostic) {
            try { $script:pendingDescendantDiagnostic.primaryMessage = $rejectionMessage } catch { }
        }
        throw $rejectionMessage
    }
    if ($diagnosticEnabled) { $script:pendingDescendantDiagnostic = $null }
    return @($activeIds)
}

function Get-PyvenvPolicy([string]$PyvenvCfg, [long]$Deadline = $deadlineQpc) {
    Assert-NoReparsePath $PyvenvCfg
    $cfgPath = [IO.Path]::GetFullPath($PyvenvCfg)
    $before = Get-FileSha256BeforeDeadline $cfgPath $Deadline
    if ($null -eq $script:pyvenvPolicyCache) { $script:pyvenvPolicyCache = @{} }
    if ($script:pyvenvPolicyCache.ContainsKey($cfgPath)) {
        $cached = $script:pyvenvPolicyCache[$cfgPath]
        if ($cached.sha256 -cne $before) { throw 'pyvenv.cfg changed after finite-profile parsing.' }
        return $cached.values
    }
    $values = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $lineNumber = 0
    foreach ($line in [IO.File]::ReadAllLines($cfgPath, [Text.Encoding]::UTF8)) {
        $lineNumber++
        if ((Get-SafeQpcValue) -ge $Deadline) { throw 'Deadline while parsing pyvenv.cfg.' }
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
        if ([char]::IsWhiteSpace($line[0])) { throw "Leading whitespace in pyvenv.cfg line $lineNumber." }
        if ($line -notmatch '^\s*([^=]+?)\s*=\s*(.*?)\s*$') { throw "Malformed pyvenv.cfg line $lineNumber." }
        $key = $matches[1].Trim()
        if ([string]::IsNullOrWhiteSpace($key) -or $values.ContainsKey($key)) { throw "Duplicate or empty pyvenv.cfg key at line $lineNumber." }
        if ($key -notin @('home','version','include-system-site-packages','executable','command')) { throw "Unsupported pyvenv.cfg key at line ${lineNumber}: $key" }
        $values.Add($key, [string]$matches[2])
    }
    foreach ($required in @('home','version','include-system-site-packages')) {
        if (-not $values.ContainsKey($required)) { throw "pyvenv.cfg omits required key: $required" }
    }
    if ($values['version'] -cne '3.13.7' -or $values['include-system-site-packages'] -cne 'false') { throw 'pyvenv.cfg differs from the pinned CPython 3.13.7 venv policy.' }
    if ((Get-FileSha256BeforeDeadline $cfgPath $Deadline) -cne $before) { throw 'pyvenv.cfg changed while it was parsed.' }
    $script:pyvenvPolicyCache[$cfgPath] = @{ sha256 = $before; values = $values }
    return $values
}

function Get-BaseInterpreter([string]$PyvenvCfg) {
    $policy = Get-PyvenvPolicy $PyvenvCfg $deadlineQpc
    $base = [IO.Path]::GetFullPath((Join-Path $policy['home'] 'python.exe'))
    Assert-NoReparsePath $base
    return $base
}

function Save-Caller([hashtable]$Record, [switch]$Terminal) {
    if (-not $callerRecordOwned -or -not $callerParentValidated) { return }
    try {
        $callerPersistenceState.secondaryCloseFailure = $null
        $callerPersistenceState.stageBeforeClose = $null
        $callerPersistenceState.recordKind = 'Caller'
        $callerPersistenceState.destinationPath = $callerPath
        $callerPersistenceState.pendingPath = $callerPath + '.update'
        $callerPersistenceState.stage = 'check-original-deadline'
        if (-not $Terminal -and [Diagnostics.Stopwatch]::GetTimestamp() -ge $deadlineQpc) {
            throw 'Original mode deadline expired before caller persistence.'
        }
        Update-OwnedJson $callerPath $Record 'Caller'
        if ([Diagnostics.Stopwatch]::GetTimestamp() -ge $deadlineQpc) {
            $Record.persistenceCompletedAfterDeadline = $true
            throw 'Caller persistence completed after the original mode deadline.'
        }
    }
    catch {
        $failure = New-CallerFailure $_ $callerPersistenceState.stage
        $failure.destinationPath = $callerPath
        $failure.pendingPath = $callerPath + '.update'
        $failure.recordKind = 'Caller'
        $failure.stageBeforeClose = $callerPersistenceState.stageBeforeClose
        $callerPersistenceState.failed = $true
        $callerPersistenceState.errors.Add($failure)
        if ($null -ne $callerPersistenceState.secondaryCloseFailure) {
            $callerPersistenceState.errors.Add($callerPersistenceState.secondaryCloseFailure)
        }
        $Record.persistenceErrors = $callerPersistenceState.errors.ToArray()
        $Record.persistenceFailed = $true
        $Record.status = 'CALLER_PERSISTENCE_FAILURE'
        $Record.wrapperChosenExitCode = 2
        throw
    }
}

function Record-HandoffPersistenceFailure($Failure) {
    $captured = New-CallerFailure $Failure $callerPersistenceState.stage
    $captured.recordKind = 'Handoff'
    $captured.destinationPath = $handoffPath
    $captured.pendingPath = $handoffPath + '.update'
    $captured.stageBeforeClose = $callerPersistenceState.stageBeforeClose
    $callerPersistenceState.failed = $true
    $callerPersistenceState.errors.Add($captured)
    if ($null -ne $callerPersistenceState.secondaryCloseFailure) {
        $secondary = $callerPersistenceState.secondaryCloseFailure
        $secondary.recordKind = 'Handoff'
        $secondary.destinationPath = $handoffPath
        $secondary.pendingPath = $handoffPath + '.update'
        $callerPersistenceState.errors.Add($secondary)
        $callerPersistenceState.secondaryCloseFailure = $null
    }
    $callerRecord.persistenceErrors = $callerPersistenceState.errors.ToArray()
    $callerRecord.persistenceFailed = $true
    $callerRecord.status = 'CALLER_PERSISTENCE_FAILURE'
    $callerRecord.wrapperChosenExitCode = 2
}

$callerRecord = @{
    schema = 'teignmouth-build3-caller-record-v2'
    mode = $Mode
    phase = if ($Mode -eq 'build') { 'reserved-build-dispatch' } elseif ($Mode -eq 'self-check') { 'nonnumerical-self-check' } else { 'standalone-identity-preparation' }
    status = 'CALLER_SETUP_STARTED'
    startedUtc = [DateTime]::UtcNow.ToString('O')
    qpcFrequency = $qpcFrequency
    startQpc = $startQpc
    deadlineQpc = $deadlineQpc
    budgetSeconds = $modeBudgetSeconds
    wrapperPid = $PID
    wrapperCreationFileTime = $null
    wrapperChosenExitCode = $null
    nativeLauncherExitCode = $null
    supervisorScriptExitCode = $null
    nativeProcessLaunched = $false
    candidateBuildExecuted = $false
    candidateEligibleForServing = $false
}

$job = [IntPtr]::Zero
$launcherProcess = [IntPtr]::Zero
$launcherThread = [IntPtr]::Zero
$scriptHandle = [IntPtr]::Zero
$processInfo = $null
$launcherResumed = $false
$launcherCreated = $false
$launcherAssigned = $false
$nativeClockReady = $false
$callerRecordOwned = $false
$callerParentValidated = $false
$handoffRecordOwned = $false
$handoffLauncherBound = $false
$handoffNonce = $null
$handoffPreparedSnapshot = $null
$handoffPreparedSha256 = $null
$callerPersistenceState = [pscustomobject]@{
    stage = 'idle'; stageBeforeClose = $null; failed = $false
    recordKind = $null; destinationPath = $null; pendingPath = $null
    secondaryCloseFailure = $null
    errors = [Collections.Generic.List[object]]::new()
}
$pendingDescendantDiagnostic = $null
$stdHandles = @()
$finalExit = 2

try {
    if ($PSVersionTable.PSVersion -lt [Version]'7.4') { throw 'PowerShell 7.4 or later is required.' }
    $parentToWrite = if ($Mode -eq 'build') { $buildRoot } else { Join-Path $root '.codex' }
    Assert-NoReparsePath $root
    Assert-NoReparsePath $parentToWrite
    if ($Mode -eq 'self-check') {
        Assert-NoReparsePath $baseEvidence -AllowMissingSuffix
        if (Test-Path -LiteralPath $baseEvidence) { throw 'Fixed self-check retry root already exists; one-shot refused.' }
        foreach ($path in @($callerPath, ($callerPath + '.update'), $callerFailurePath, $handoffPath, ($handoffPath + '.update'),
            $consumedPath, $scriptStartPath, $stdoutPath, $stderrPath, $ownedRunLeaf)) {
            if (Test-Path -LiteralPath $path) { throw "Fixed self-check retry evidence already exists: $path" }
        }
        # An absent run-1 also establishes absence of all fixed helper descendants.
        New-Item -ItemType Directory -Path $baseEvidence -ErrorAction Stop | Out-Null
    }
    if ($Mode -ne 'build' -and -not (Test-Path -LiteralPath $baseEvidence)) {
        New-Item -ItemType Directory -Path $baseEvidence -Force | Out-Null
    }
    Assert-NoReparsePath $baseEvidence
    $callerParentValidated = $true
    if ($Mode -eq 'build' -and -not (Test-Path -LiteralPath $buildRoot -PathType Container)) {
        throw 'Fixed build-3 metadata directory is unavailable.'
    }
    foreach ($path in @($callerPath, ($callerPath + '.update'), $handoffPath, ($handoffPath + '.update'), $consumedPath, $scriptStartPath)) {
        if (Test-Path -LiteralPath $path) { throw "Fixed one-use path already exists: $path" }
    }
    if ($Mode -eq 'build') {
        foreach ($path in @(
            (Join-Path $buildRoot 'invocation.json'),
            (Join-Path $buildRoot 'run-1'),
            (Join-Path $root 'data\generated\teignmouth-float32-topology')
        )) {
            if (Test-Path -LiteralPath $path) { throw "Build-3 fixed output path is already occupied: $path" }
        }
    }
    elseif (Test-Path -LiteralPath $ownedRunLeaf) {
        throw "Fixed standalone evidence run leaf is already occupied: $ownedRunLeaf"
    }
    $callerRecord.handoffPath = $handoffPath
    $callerRecord.consumedHandoffPath = $consumedPath
    Write-ExclusiveJson $callerPath $callerRecord
    $callerRecordOwned = $true

    $interop = @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class TeignmouthBuild3Native {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct STARTUPINFO { public int cb; public string reserved; public string desktop; public string title; public int x,y,xSize,ySize,xChars,yChars,fill,flags; public short show,reserved2; public IntPtr reservedPtr,stdin,stdout,stderr; }
  [StructLayout(LayoutKind.Sequential)] public struct PROCESS_INFORMATION { public IntPtr process,thread; public uint processId,threadId; }
  [StructLayout(LayoutKind.Sequential)] public struct SECURITY_ATTRIBUTES { public int length; public IntPtr descriptor; [MarshalAs(UnmanagedType.Bool)] public bool inherit; }
  [StructLayout(LayoutKind.Sequential)] public struct BASIC_LIMIT { public long processTime,jobTime; public uint flags; public UIntPtr minWs,maxWs; public uint active; public UIntPtr affinity; public uint priority,scheduling; }
  [StructLayout(LayoutKind.Sequential)] public struct IO_COUNTERS { public ulong readOps,writeOps,otherOps,readBytes,writeBytes,otherBytes; }
  [StructLayout(LayoutKind.Sequential)] public struct EXTENDED_LIMIT { public BASIC_LIMIT basic; public IO_COUNTERS io; public UIntPtr processMemory,jobMemory,peakProcess,peakJob; }
  [StructLayout(LayoutKind.Sequential)] public struct BASIC_ACCOUNTING { public long user,kernel,periodUser,periodKernel; public uint pageFaults,total,active,terminated; }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct PROCESSENTRY { public uint size,usage,pid; public UIntPtr heap; public uint module,threads,parent; public int priority; public uint flags; [MarshalAs(UnmanagedType.ByValTStr,SizeConst=260)] public string image; }
  [StructLayout(LayoutKind.Sequential)] public struct PROCESSROW { public uint processId,parentPid; }
  [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern IntPtr CreateJobObject(IntPtr attrs,string name);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetInformationJobObject(IntPtr job,int kind,ref EXTENDED_LIMIT info,uint size);
  [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref STARTUPINFO si,out PROCESS_INFORMATION pi);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern uint ResumeThread(IntPtr thread);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetExitCodeProcess(IntPtr process,out uint code);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool TerminateJobObject(IntPtr job,uint code);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool TerminateProcess(IntPtr process,uint code);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool CloseHandle(IntPtr handle);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetProcessTimes(IntPtr process,out long creation,out long exit,out long kernel,out long user);
  [DllImport("kernel32.dll",EntryPoint="QueryFullProcessImageNameW",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder path,ref uint length);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool result);
  [DllImport("kernel32.dll",SetLastError=true)] public static extern bool QueryInformationJobObject(IntPtr job,int kind,IntPtr buffer,uint length,out uint returned);
  [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern IntPtr CreateFile(string path,uint access,uint share,ref SECURITY_ATTRIBUTES attrs,uint creation,uint flags,IntPtr template);
  [DllImport("kernel32.dll")] public static extern bool QueryPerformanceCounter(out long value);
  [DllImport("kernel32.dll")] public static extern bool QueryPerformanceFrequency(out long value);
  [DllImport("kernel32.dll")] public static extern IntPtr GetCurrentProcess();
  [DllImport("kernel32.dll")] public static extern uint GetCurrentProcessId();
  [DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr CreateToolhelp32Snapshot(uint flags,uint pid);
  [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool Process32First(IntPtr snap,ref PROCESSENTRY row);
  [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool Process32Next(IntPtr snap,ref PROCESSENTRY row);
  private static void CheckDeadline(long deadline) { long now; if(!QueryPerformanceCounter(out now) || now>=deadline) throw new TimeoutException("QPC deadline reached during native census"); }
  public static uint ParentPid(uint pid,long deadline) { CheckDeadline(deadline); IntPtr s=CreateToolhelp32Snapshot(2,0); if(s==new IntPtr(-1)) throw new System.ComponentModel.Win32Exception(); try { PROCESSENTRY e=new PROCESSENTRY(); e.size=(uint)Marshal.SizeOf(typeof(PROCESSENTRY)); if(!Process32First(s,ref e)) throw new System.ComponentModel.Win32Exception(); for(int i=0;i<65536;i++){ CheckDeadline(deadline); if(e.pid==pid)return e.parent; if(!Process32Next(s,ref e))break; } throw new InvalidOperationException("PID missing from bounded snapshot"); } finally { CloseHandle(s); } }
  public static List<PROCESSROW> GetProcessRows(long deadline) { CheckDeadline(deadline); IntPtr s=CreateToolhelp32Snapshot(2,0); if(s==new IntPtr(-1)) throw new System.ComponentModel.Win32Exception(); try { List<PROCESSROW> a=new List<PROCESSROW>(); PROCESSENTRY e=new PROCESSENTRY(); e.size=(uint)Marshal.SizeOf(typeof(PROCESSENTRY)); if(!Process32First(s,ref e)) throw new System.ComponentModel.Win32Exception(); for(int i=0;i<65536;i++){ CheckDeadline(deadline); a.Add(new PROCESSROW{processId=e.pid,parentPid=e.parent}); if(!Process32Next(s,ref e))return a; } throw new InvalidOperationException("Process snapshot exceeds bound"); } finally { CloseHandle(s); } }
  public static List<PROCESSROW> GetProcessRows(long deadline,out int terminalError) { terminalError=-1; CheckDeadline(deadline); IntPtr s=CreateToolhelp32Snapshot(2,0); if(s==new IntPtr(-1)) throw new System.ComponentModel.Win32Exception(); try { List<PROCESSROW> a=new List<PROCESSROW>(); PROCESSENTRY e=new PROCESSENTRY(); e.size=(uint)Marshal.SizeOf(typeof(PROCESSENTRY)); if(!Process32First(s,ref e)) throw new System.ComponentModel.Win32Exception(); for(int i=0;i<65536;i++){ CheckDeadline(deadline); a.Add(new PROCESSROW{processId=e.pid,parentPid=e.parent}); if(!Process32Next(s,ref e)){ terminalError=Marshal.GetLastWin32Error(); return a; } } throw new InvalidOperationException("Process snapshot exceeds bound"); } finally { CloseHandle(s); } }
  public static uint[] GetJobProcessIds(IntPtr job,long deadline) { int cap=32; for(int attempt=0;attempt<8;attempt++){ CheckDeadline(deadline); int size=8+IntPtr.Size*cap; IntPtr p=Marshal.AllocHGlobal(size); try { uint got; bool ok=QueryInformationJobObject(job,3,p,(uint)size,out got); uint assigned=(uint)Marshal.ReadInt32(p,0); uint listed=(uint)Marshal.ReadInt32(p,4); if(ok){ if(listed>cap)throw new InvalidOperationException("Job process list count invalid"); uint[] ids=new uint[listed]; for(int i=0;i<listed;i++){ CheckDeadline(deadline); ids[i]=IntPtr.Size==8?(uint)Marshal.ReadInt64(p,8+i*IntPtr.Size):(uint)Marshal.ReadInt32(p,8+i*IntPtr.Size); } return ids; } int need=Math.Max((int)assigned,(int)((got>8?(got-8)/IntPtr.Size:0)+8)); cap=Math.Max(cap*2,need); if(cap>65536)throw new InvalidOperationException("Job process census exceeds bound"); } finally { Marshal.FreeHGlobal(p); } } throw new InvalidOperationException("Job process census retry bound exceeded"); }
}
'@
    Add-Type -TypeDefinition $interop
    $nativeFrequency = [long]0
    if (-not [TeignmouthBuild3Native]::QueryPerformanceFrequency([ref]$nativeFrequency) -or
        $nativeFrequency -ne $qpcFrequency) { throw 'PowerShell and native QPC frequency differs.' }
    $nativeClockReady = $true

    $parentCreated = [long]0; $parentExited = [long]0; $parentKernel = [long]0; $parentUser = [long]0
    if (-not [TeignmouthBuild3Native]::GetProcessTimes(
        [TeignmouthBuild3Native]::GetCurrentProcess(),
        [ref]$parentCreated, [ref]$parentExited, [ref]$parentKernel, [ref]$parentUser
    )) { throw 'Cannot record wrapper process identity.' }
    $callerRecord.wrapperCreationFileTime = $parentCreated
    Save-Caller $callerRecord

    Assert-NoReparsePath $python
    Assert-NoReparsePath $supervisor
    $pyvenvCfg = Join-Path $root 'pipeline\.venv\pyvenv.cfg'
    $baseInterpreter = Get-BaseInterpreter $pyvenvCfg
    $launcherHash = (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()
    $baseHash = (Get-FileHash -LiteralPath $baseInterpreter -Algorithm SHA256).Hash.ToLowerInvariant()
    $wrapperIdentity = Get-NativeIdentity $PID $deadlineQpc
$manifestSha = $null; $externalSha = $null; $snapshotSha = $null; $authSha = $null
$runtimeIdentitySha = $null
$standalonePurpose = $null
    if ($Mode -eq 'build') {
        $inputManifest = Join-Path $buildRoot 'input-manifest.json'
        $externalManifest = Join-Path $buildRoot 'external-runtime-manifest.json'
        $snapshot = Join-Path $buildRoot 'reserved-ledger-snapshot.json'
        $runtimeIdentityPath = Join-Path $buildRoot 'runtime-identity.json'
        foreach ($protectedPath in @($inputManifest,$externalManifest,$snapshot,$runtimeIdentityPath)) { Assert-NoReparsePath $protectedPath }
        $manifestSha = (Get-FileHash -LiteralPath $inputManifest -Algorithm SHA256).Hash.ToLowerInvariant()
        $externalSha = (Get-FileHash -LiteralPath $externalManifest -Algorithm SHA256).Hash.ToLowerInvariant()
        $snapshotSha = (Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash.ToLowerInvariant()
        $runtimeIdentitySha = (Get-FileHash -LiteralPath $runtimeIdentityPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $closure = Test-StandaloneFrozenClosure $inputManifest $externalManifest $runtimeIdentityPath $deadlineQpc $callerRecord
        if (-not $closure.passes -or
            $closure.repositoryCheckedCount -ne $closure.repositoryDeclaredCount -or
            $closure.externalCheckedCount -ne $closure.externalDeclaredCount -or
            $closure.inputManifestSha256 -ne $manifestSha -or
            $closure.externalRuntimeManifestSha256 -ne $externalSha -or
            $closure.runtimeIdentitySha256 -ne $runtimeIdentitySha) {
            throw 'Build finite startup/runtime closure failed before executable launch.'
        }
        $callerRecord.standaloneFrozenClosureBeforeLaunch = $closure
        Save-Caller $callerRecord
    }
    elseif ($Mode -eq 'runtime-preflight') {
        $authorizationPath = Join-Path $buildRoot 'runtime-preflight-authorization.json'
        Assert-NoReparsePath $authorizationPath
        $authorization = Get-Content -LiteralPath $authorizationPath -Raw | ConvertFrom-Json -AsHashtable
        if ($authorization.schema -ne 'teignmouth-build3-runtime-preflight-authorization-v2' -or
            $authorization.authorized -ne $true -or $authorization.oneShot -ne $true -or
            $authorization.purpose -notin @('collect-unreserved-runtime-identity','verify-unreserved-runtime-identity')) {
            throw 'Standalone identity preparation lacks exact coordinator authorization.'
        }
        $authSha = (Get-FileHash -LiteralPath $authorizationPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $standalonePurpose = $authorization.purpose
        if ($standalonePurpose -eq 'verify-unreserved-runtime-identity') {
            $inputManifest = Join-Path $buildRoot 'input-manifest.json'
            $externalManifest = Join-Path $buildRoot 'external-runtime-manifest.json'
            $runtimeIdentityPath = Join-Path $buildRoot 'runtime-identity.json'
            foreach ($protectedPath in @($inputManifest,$externalManifest,$runtimeIdentityPath)) { Assert-NoReparsePath $protectedPath }
            $manifestSha = (Get-FileHash -LiteralPath $inputManifest -Algorithm SHA256).Hash.ToLowerInvariant()
            $externalSha = (Get-FileHash -LiteralPath $externalManifest -Algorithm SHA256).Hash.ToLowerInvariant()
            $runtimeIdentitySha = (Get-FileHash -LiteralPath $runtimeIdentityPath -Algorithm SHA256).Hash.ToLowerInvariant()
            $closure = Test-StandaloneFrozenClosure $inputManifest $externalManifest $runtimeIdentityPath $deadlineQpc $callerRecord
            if (-not $closure.passes -or
                $closure.repositoryCheckedCount -ne $closure.repositoryDeclaredCount -or
                $closure.externalCheckedCount -ne $closure.externalDeclaredCount -or
                $closure.inputManifestSha256 -ne $manifestSha -or
                $closure.externalRuntimeManifestSha256 -ne $externalSha -or
                $closure.runtimeIdentitySha256 -ne $runtimeIdentitySha) {
                throw 'Standalone frozen runtime closure failed before executable launch.'
            }
            $callerRecord.standaloneFrozenClosureBeforeLaunch = $closure
            Save-Caller $callerRecord
        }
    }
    if ((Get-SafeQpcValue) -ge $deadlineQpc) { throw 'Mode deadline expired during fixed input hashing.' }
    $nonce = [Guid]::NewGuid().ToString('N')
    $handoffNonce = $nonce
    $handoffRecord = @{
        schema = 'teignmouth-build3-parent-handoff-v2'; mode = $Mode; oneUse = $true; phase = $callerRecord.phase
        nonce = $nonce; clockDomain = 'windows-qpc'; qpcFrequency = $qpcFrequency
        startQpc = $startQpc; deadlineQpc = $deadlineQpc; budgetSeconds = $modeBudgetSeconds
        wrapperPid = $PID; wrapperCreationFileTime = $parentCreated
        wrapperImagePath = $wrapperIdentity.imagePath; wrapperImageSha256 = $wrapperIdentity.imageSha256
        expectedSupervisorScript = [IO.Path]::GetFullPath($supervisor)
        launcherPath = [IO.Path]::GetFullPath($python); launcherSha256 = $launcherHash
        baseInterpreterPath = $baseInterpreter; baseInterpreterSha256 = $baseHash
        launcherPid = $null; launcherCreationFileTime = $null; launcherImagePath = $null
        launcherImageSha256 = $null
        inputManifestSha256 = $manifestSha; externalRuntimeManifestSha256 = $externalSha
        reservedLedgerSnapshotSha256 = $snapshotSha; standaloneAuthorizationSha256 = $authSha
        runtimeIdentitySha256 = $runtimeIdentitySha
        standalonePurpose = $standalonePurpose
        status = 'PREPARED'
    }
    $callerPersistenceState.recordKind = 'Handoff'
    $callerPersistenceState.destinationPath = $handoffPath
    $callerPersistenceState.pendingPath = $handoffPath + '.update'
    $callerPersistenceState.secondaryCloseFailure = $null
    $callerPersistenceState.stageBeforeClose = $null
    $callerPersistenceState.stage = 'create-exclusive-prepared-handoff'
    try {
        Write-ExclusiveJson $handoffPath $handoffRecord
        $handoffRecordOwned = $true
        $handoffPreparedSnapshot = @{}
        foreach ($key in $handoffRecord.Keys) { $handoffPreparedSnapshot[[string]$key] = $handoffRecord[$key] }
        $callerPersistenceState.stage = 'hash-prepared-handoff'
        $handoffPreparedSha256 = Get-FileSha256BeforeDeadline $handoffPath $deadlineQpc
        Assert-ExactHandoffRecord (Get-TrustedPreparedHandoff) $handoffPreparedSnapshot 'In-memory prepared'
        if ((Get-FileSha256BeforeDeadline $handoffPath $deadlineQpc) -cne $handoffPreparedSha256) {
            throw 'Prepared handoff changed while its owned snapshot was captured.'
        }
        $callerPersistenceState.stage = 'parse-prepared-handoff'
        $persistedPrepared = [IO.File]::ReadAllText($handoffPath) | ConvertFrom-Json -AsHashtable
        Assert-ExactHandoffRecord $handoffPreparedSnapshot $persistedPrepared 'Persisted prepared'
        if ((Get-FileSha256BeforeDeadline $handoffPath $deadlineQpc) -cne $handoffPreparedSha256) {
            throw 'Prepared handoff changed while its identity was parsed.'
        }
    }
    catch {
        Record-HandoffPersistenceFailure $_
        throw
    }
    $callerRecord.status = 'HANDOFF_PREPARED'
    $callerRecord.nonce = $nonce
    $callerRecord.launcherPath = $python
    $callerRecord.launcherSha256 = $launcherHash
    $callerRecord.baseInterpreterPath = $baseInterpreter
    $callerRecord.baseInterpreterSha256 = $baseHash
    $callerRecord.inputManifestSha256 = $manifestSha
    $callerRecord.externalRuntimeManifestSha256 = $externalSha
    $callerRecord.reservedLedgerSnapshotSha256 = $snapshotSha
    $callerRecord.runtimeIdentitySha256 = $runtimeIdentitySha
    $callerRecord.standaloneAuthorizationSha256 = $authSha
    Save-Caller $callerRecord

    $job = [TeignmouthBuild3Native]::CreateJobObject([IntPtr]::Zero, $null)
    if ($job -eq [IntPtr]::Zero) { throw 'CreateJobObject failed.' }
    $limits = New-Object TeignmouthBuild3Native+EXTENDED_LIMIT
    $limits.basic.flags = 0x00002000
    if (-not [TeignmouthBuild3Native]::SetInformationJobObject(
        $job, 9, [ref]$limits, [uint32][Runtime.InteropServices.Marshal]::SizeOf($limits)
    )) { throw 'Cannot configure kill-on-close outer Job Object.' }
    $security = New-Object TeignmouthBuild3Native+SECURITY_ATTRIBUTES
    $security.length = [Runtime.InteropServices.Marshal]::SizeOf($security)
    $security.inherit = $true
    $stdin = [TeignmouthBuild3Native]::CreateFile('NUL',0x80000000u,3,[ref]$security,3,0x80,[IntPtr]::Zero)
    $outHandle = [TeignmouthBuild3Native]::CreateFile($stdoutPath,0x40000000u,1,[ref]$security,1,0x80,[IntPtr]::Zero)
    $errHandle = [TeignmouthBuild3Native]::CreateFile($stderrPath,0x40000000u,1,[ref]$security,1,0x80,[IntPtr]::Zero)
    $stdHandles = @($stdin,$outHandle,$errHandle)
    if ($stdHandles | Where-Object { $_ -eq [IntPtr]::Zero -or $_ -eq [IntPtr](-1) }) {
        throw 'Cannot create fixed stdout/stderr handles.'
    }
    $startup = New-Object TeignmouthBuild3Native+STARTUPINFO
    $startup.cb = [Runtime.InteropServices.Marshal]::SizeOf($startup)
    $startup.flags = 0x100; $startup.stdin = $stdin; $startup.stdout = $outHandle; $startup.stderr = $errHandle
    $commandLine = '"' + $python + '" ' + (($launcherArguments | ForEach-Object { '"' + $_ + '"' }) -join ' ')
    $commandBuffer = New-Object Text.StringBuilder $commandLine
    $processInfo = New-Object TeignmouthBuild3Native+PROCESS_INFORMATION
    if (-not [TeignmouthBuild3Native]::CreateProcess(
        $python,$commandBuffer,[IntPtr]::Zero,[IntPtr]::Zero,$true,0x00000004 -bor 0x08000000,
        [IntPtr]::Zero,$root,[ref]$startup,[ref]$processInfo
    )) { throw 'CreateProcessW for the approved venv launcher failed.' }
    $launcherProcess = $processInfo.process
    $launcherThread = $processInfo.thread
    $launcherCreated = $true
    $callerRecord.nativeProcessLaunched = $true
    $launcherIdentity = Get-NativeIdentity $processInfo.processId $deadlineQpc
    if ($launcherIdentity.imagePath -ne [IO.Path]::GetFullPath($python) -or
        $launcherIdentity.imageSha256 -ne $launcherHash) { throw 'Suspended launcher native image/hash mismatch.' }
    $handoffRecord.launcherPid = [uint32]$processInfo.processId
    $handoffRecord.launcherCreationFileTime = $launcherIdentity.creationFileTime
    $handoffRecord.launcherImagePath = $launcherIdentity.imagePath
    $handoffRecord.launcherImageSha256 = $launcherIdentity.imageSha256
    $handoffRecord.status = 'LAUNCHER_BOUND_BEFORE_RESUME'
    $callerPersistenceState.recordKind = 'Handoff'
    $callerPersistenceState.destinationPath = $handoffPath
    $callerPersistenceState.pendingPath = $handoffPath + '.update'
    $callerPersistenceState.secondaryCloseFailure = $null
    $callerPersistenceState.stageBeforeClose = $null
    $callerPersistenceState.stage = 'check-original-deadline-before-handoff-update'
    try {
        if ((Get-SafeQpcValue) -ge $deadlineQpc) { throw 'Original mode deadline expired before handoff update.' }
        Update-OwnedJson $handoffPath $handoffRecord 'Handoff'
        if ((Get-SafeQpcValue) -ge $deadlineQpc) {
            $callerPersistenceState.stage = 'handoff-update-completed-after-deadline'
            throw 'Handoff update completed after the original mode deadline.'
        }
    }
    catch {
        Record-HandoffPersistenceFailure $_
        throw
    }
    if (-not [TeignmouthBuild3Native]::AssignProcessToJobObject($job,$launcherProcess)) {
        throw 'Cannot assign approved launcher to outer Job before resume.'
    }
    $launcherAssigned = $true
    $inOuterJob = $false
    if (-not [TeignmouthBuild3Native]::IsProcessInJob($launcherProcess,$job,[ref]$inOuterJob) -or -not $inOuterJob) {
        throw 'Suspended launcher is not a member of the exact outer Job.'
    }
    $callerRecord.outerJobAssignmentConfirmed = $true
    Save-Caller $callerRecord
    foreach ($handle in $stdHandles) { [void][TeignmouthBuild3Native]::CloseHandle($handle) }
    $stdHandles = @()
    if ((Get-RemainingMilliseconds $deadlineQpc $qpcFrequency) -le 0) { throw 'Mode deadline expired before launcher resume.' }
    if ([TeignmouthBuild3Native]::ResumeThread($launcherThread) -eq [uint32]::MaxValue) {
        throw 'ResumeThread for approved venv launcher failed.'
    }
    $launcherResumed = $true
    $callerRecord.status = 'LAUNCHER_RUNNING'
    Save-Caller $callerRecord

    $scriptIdentity = $null
    $probeDeadline = [Math]::Min($deadlineQpc, $startQpc + [long][Math]::Ceiling([Math]::Min(3.0,$modeBudgetSeconds * 0.25) * $qpcFrequency))
    while ((Get-QpcValue) -lt $probeDeadline) {
        $null = Assert-OwnedJobTree $job @([uint32]$processInfo.processId)
        if (Test-Path -LiteralPath $scriptStartPath -PathType Leaf) {
            try { $scriptIdentity = Get-Content -LiteralPath $scriptStartPath -Raw | ConvertFrom-Json -AsHashtable }
            catch { $scriptIdentity = $null }
            if ($scriptIdentity) { break }
        }
        $remaining = Get-RemainingMilliseconds $probeDeadline $qpcFrequency
        if ($remaining -le 0) { break }
        [void][TeignmouthBuild3Native]::WaitForSingleObject($launcherProcess,[uint32][Math]::Min($remaining,50))
    }
    if (-not $scriptIdentity) { throw 'Supervisor interpreter did not publish its fixed script-start identity before deadline.' }
    $scriptPid = [uint32]$scriptIdentity.scriptPid
    $scriptNative = Get-NativeIdentity $scriptPid $deadlineQpc
    if ($scriptPid -eq [uint32]$processInfo.processId -or
        $scriptNative.creationFileTime -ne [long]$scriptIdentity.scriptCreationFileTime -or
        $scriptNative.imagePath -ne $baseInterpreter -or
        $scriptNative.imageSha256 -ne $baseHash -or
        [TeignmouthBuild3Native]::ParentPid($scriptPid,$deadlineQpc) -ne [uint32]$processInfo.processId -or
        [TeignmouthBuild3Native]::ParentPid([uint32]$processInfo.processId,$deadlineQpc) -ne [uint32]$PID -or
        $scriptIdentity.launcherPid -ne [uint32]$processInfo.processId -or
        $scriptIdentity.launcherCreationFileTime -ne $launcherIdentity.creationFileTime -or
        $scriptIdentity.wrapperPid -ne [uint32]$PID -or
        $scriptIdentity.nonce -ne $nonce) {
        throw 'Supervisor venv-launcher → base-interpreter ancestry or identity mismatch.'
    }
    $scriptHandle = [TeignmouthBuild3Native]::OpenProcess(0x1000 -bor 0x0400,$false,$scriptPid)
    if ($scriptHandle -eq [IntPtr]::Zero) { throw 'Cannot retain supervisor interpreter process handle.' }
    $inOuterJob = $false
    if (-not [TeignmouthBuild3Native]::IsProcessInJob($scriptHandle,$job,[ref]$inOuterJob) -or -not $inOuterJob) {
        throw 'Supervisor base interpreter is not a member of the outer Job.'
    }
    $null = Assert-OwnedJobTree $job @([uint32]$processInfo.processId,$scriptPid)
    $callerRecord.supervisorLauncherIdentity = $launcherIdentity
    $callerRecord.supervisorScriptIdentity = $scriptIdentity
    $callerRecord.outerJobMembershipObserved = $true
    Save-Caller $callerRecord

    $nativeLauncherExit = $null
    $scriptExit = $null
    $timedOut = $false
    while ($true) {
        $null = Assert-OwnedJobTree $job @([uint32]$processInfo.processId,$scriptPid)
        $remaining = Get-RemainingMilliseconds $deadlineQpc $qpcFrequency
        if ($remaining -le 0) { $timedOut = $true; break }
        $wait = [TeignmouthBuild3Native]::WaitForSingleObject(
            $launcherProcess,[uint32][Math]::Min($remaining,100)
        )
        if ($wait -eq 0) { break }
        if ($wait -ne 258) { throw 'WaitForSingleObject failed for launcher handle.' }
    }
    if ($timedOut) {
        $callerRecord.status = 'STOP_OUTER_DEADLINE'
        $callerRecord.timeout = $true
        $callerRecord.forcedContainment = $true
        [void][TeignmouthBuild3Native]::TerminateJobObject($job,124)
    }
    $activeOuter = [TeignmouthBuild3Native]::GetJobProcessIds($job,$deadlineQpc)
    if ($activeOuter.Count -gt 0) {
        $callerRecord.unexpectedOuterJobProcesses = @($activeOuter)
        $callerRecord.forcedContainment = $true
        $callerRecord.status = 'STOP_OUTER_DESCENDANTS_REMAINED'
        [void][TeignmouthBuild3Native]::TerminateJobObject($job,2)
    }
    if ($activeOuter.Count -eq 0) { $callerRecord.outerTerminationConfirmed = $true }
    $exitCode = [uint32]0
    if ([TeignmouthBuild3Native]::GetExitCodeProcess($launcherProcess,[ref]$exitCode) -and $exitCode -ne 259) {
        $nativeLauncherExit = [int64]$exitCode
    }
    $callerRecord.nativeLauncherExitCode = $nativeLauncherExit
    $scriptCode = [uint32]0
    if ($scriptHandle -ne [IntPtr]::Zero -and
        [TeignmouthBuild3Native]::GetExitCodeProcess($scriptHandle,[ref]$scriptCode) -and $scriptCode -ne 259) {
        $scriptExit = [int64]$scriptCode
    }
    $callerRecord.supervisorScriptExitCode = $scriptExit
    $callerRecord.elapsedSeconds = ((Get-QpcValue) - $startQpc) / [double]$qpcFrequency
    $callerRecord.deadlinePassed = (Get-QpcValue) -lt $deadlineQpc
    $callerRecord.wrapperChosenExitCode = if (
        $callerRecord.deadlinePassed -and $callerRecord.outerTerminationConfirmed -and
        -not $callerRecord.forcedContainment -and $null -ne $nativeLauncherExit -and
        $nativeLauncherExit -eq 0 -and $null -ne $scriptExit -and $scriptExit -eq 0
    ) { 0 } else { 2 }
    if ($callerRecord.wrapperChosenExitCode -eq 0) { $callerRecord.status = 'CALLER_COMPLETED' }
    elseif (-not $callerRecord.status.StartsWith('STOP_')) { $callerRecord.status = 'CALLER_BLOCKED' }
    $finalExit = [int]$callerRecord.wrapperChosenExitCode
}
catch {
    # Capture before cleanup/clock/persistence operations can report secondary errors.
    if (-not $callerPersistenceState.failed) {
        $callerRecord.primaryError = New-CallerFailure $_ 'setup-or-supervision'
        $callerRecord.status = 'CALLER_SETUP_OR_SUPERVISION_FAILURE'
        $callerRecord.error = $callerRecord.primaryError.message
    }
    $callerRecord.wrapperChosenExitCode = 2
    $finalExit = 2
    if ($launcherCreated -and $launcherProcess -ne [IntPtr]::Zero -and -not $launcherAssigned) {
        try {
            $terminated = [TeignmouthBuild3Native]::TerminateProcess($launcherProcess, 2)
            $callerRecord.unassignedLauncherTerminationRequested = $terminated
            $left = Get-RemainingMilliseconds $deadlineQpc $qpcFrequency
            $waitResult = [TeignmouthBuild3Native]::WaitForSingleObject(
                $launcherProcess,[uint32][Math]::Min($left,1000)
            )
            $callerRecord.unassignedLauncherWaitResult = $waitResult
            $callerRecord.unassignedLauncherTerminationConfirmed = $waitResult -eq 0
            if ($left -le 0) { $callerRecord.unassignedLauncherWaitStatus = 'nonblocking-deadline-observation' }
            if ($callerRecord.unassignedLauncherTerminationConfirmed) {
                $unassignedExit = [uint32]0
                if ([TeignmouthBuild3Native]::GetExitCodeProcess($launcherProcess,[ref]$unassignedExit) -and
                    $unassignedExit -ne 259) {
                    $callerRecord.nativeLauncherExitCode = [int64]$unassignedExit
                }
            }
        }
        catch { $callerRecord.unassignedLauncherCleanupError = $_.Exception.Message }
    }
    elseif ($job -ne [IntPtr]::Zero -and $launcherAssigned) {
        try {
            [void][TeignmouthBuild3Native]::TerminateJobObject($job,2)
            $callerRecord.forcedContainment = $true
            $cleanupRemaining = Get-RemainingMilliseconds $deadlineQpc $qpcFrequency
            $callerRecord.cleanupRemainingMilliseconds = $cleanupRemaining
            if ($launcherProcess -ne [IntPtr]::Zero -and $cleanupRemaining -gt 0) {
                [void][TeignmouthBuild3Native]::WaitForSingleObject(
                    $launcherProcess,[uint32][Math]::Min($cleanupRemaining,1000)
                )
            }
            $remainingIds = [TeignmouthBuild3Native]::GetJobProcessIds($job,$deadlineQpc)
            $callerRecord.outerProcessesAfterCleanup = @($remainingIds)
            $callerRecord.outerTerminationConfirmed = $remainingIds.Count -eq 0
        }
        catch { $callerRecord.cleanupError = $_.Exception.Message }
    }
    if ($launcherProcess -ne [IntPtr]::Zero) {
        $code = [uint32]0
        if ([TeignmouthBuild3Native]::GetExitCodeProcess($launcherProcess,[ref]$code) -and $code -ne 259) {
            $callerRecord.nativeLauncherExitCode = [int64]$code
        }
    }
    try {
        $errorQpc = Get-SafeQpcValue
        $callerRecord.elapsedSeconds = ($errorQpc - $startQpc) / [double]$qpcFrequency
        $callerRecord.deadlinePassed = $errorQpc -lt $deadlineQpc
    }
    catch {
        $callerRecord.clockTelemetryStatus = 'unavailable'
        $callerRecord.clockTelemetryError = New-CallerFailure $_ 'failure-clock-telemetry'
    }
    if (-not $callerPersistenceState.failed -and $null -ne $script:pendingDescendantDiagnostic -and
        $null -ne $callerRecord.primaryError -and
        $callerRecord.primaryError.message -ceq $script:pendingDescendantDiagnostic.primaryMessage) {
        try {
            $diagnosticJson = Convert-FalseMembershipObservation $script:pendingDescendantDiagnostic
            if ($null -ne $diagnosticJson -and (Get-SafeQpcValue) -lt $deadlineQpc) {
                $combinedMessage = [string]$callerRecord.primaryError.message + "`nDescendant evidence: " + [string]$diagnosticJson
                $callerRecord.primaryError.message = $combinedMessage
                $callerRecord.error = $combinedMessage
            }
        } catch { }
    }
}
finally {
    $callerRecord.launcherCreated = $launcherCreated
    $callerRecord.launcherAssigned = $launcherAssigned
    $callerRecord.launcherResumed = $launcherResumed
    $cleanupErrors = [Collections.Generic.List[object]]::new()
    foreach ($handle in $stdHandles) {
        if ($handle -ne [IntPtr]::Zero -and $handle -ne [IntPtr](-1)) {
            try { [void][TeignmouthBuild3Native]::CloseHandle($handle) }
            catch { $cleanupErrors.Add((New-CallerFailure $_ 'close-standard-handle')) }
        }
    }
    $stdHandles = @()
    foreach ($ownedHandle in @(
        @{ name = 'job'; value = $job }, @{ name = 'launcher-thread'; value = $launcherThread },
        @{ name = 'launcher-process'; value = $launcherProcess }, @{ name = 'script-process'; value = $scriptHandle }
    )) {
        if ($ownedHandle.value -ne [IntPtr]::Zero) {
            try { [void][TeignmouthBuild3Native]::CloseHandle($ownedHandle.value) }
            catch { $cleanupErrors.Add((New-CallerFailure $_ ('close-' + $ownedHandle.name))) }
        }
    }
    $job = [IntPtr]::Zero; $launcherThread = [IntPtr]::Zero
    $launcherProcess = [IntPtr]::Zero; $scriptHandle = [IntPtr]::Zero
    if ($cleanupErrors.Count -gt 0) {
        $callerRecord.handleCleanupErrors = $cleanupErrors.ToArray()
        $callerRecord.status = 'CALLER_CLEANUP_FAILURE'
        $callerRecord.wrapperChosenExitCode = 2
        $finalExit = 2
    }
    $callerRecord.wrapperActualNativeExitCaptured = $null -ne $callerRecord.nativeLauncherExitCode
    $callerRecord.finishedUtc = [DateTime]::UtcNow.ToString('O')
    try {
        $finalQpc = Get-SafeQpcValue
        $callerRecord.elapsedSeconds = ($finalQpc - $startQpc) / [double]$qpcFrequency
        $callerRecord.deadlinePassed = $finalQpc -lt $deadlineQpc
        if (-not $callerRecord.deadlinePassed) {
            $callerRecord.status = 'CALLER_DEADLINE_FAILURE'
            $callerRecord.wrapperChosenExitCode = 2
            $finalExit = 2
        }
    }
    catch {
        $callerRecord.clockTelemetryStatus = 'unavailable'
        $callerRecord.clockTelemetryError = New-CallerFailure $_ 'final-clock-telemetry'
        $callerRecord.status = 'CALLER_CLOCK_TELEMETRY_FAILURE'
        $callerRecord.wrapperChosenExitCode = 2
        $finalExit = 2
    }
    if ($callerPersistenceState.failed) {
        $callerRecord.status = 'CALLER_PERSISTENCE_FAILURE'
        $callerRecord.wrapperChosenExitCode = 2
        $finalExit = 2
    }
    if ($callerRecordOwned -and $callerParentValidated) {
        try { Save-Caller $callerRecord -Terminal }
        catch {
            $finalExit = 2
            $callerRecord.terminalPersistenceError = New-CallerFailure $_ $callerPersistenceState.stage
            $callerRecord.wrapperChosenExitCode = 2
            try { Write-CallerTerminalFailure $callerRecord }
            catch {
                $callerRecord.fallbackPersistenceError = New-CallerFailure $_ 'exclusive-terminal-fallback'
                $callerRecord.durableErrorTelemetryStatus = 'unavailable'
                try {
                    [Console]::Error.WriteLine('Caller persistence failed; durable terminal telemetry is unavailable.')
                    [Console]::Error.WriteLine(($callerRecord | ConvertTo-Json -Depth 12 -Compress))
                }
                catch { } # Reporting must never replace exit 2 or bypass cleanup.
            }
        }
    }
}
exit $finalExit
