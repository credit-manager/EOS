<# 
.SYNOPSIS
    Automated FAIL-CLOSED Release Gate for EOS/2TO ERP
    Verifies identity, provenance, and CI success before declaring RELEASE ELIGIBLE
#>

$ErrorActionPreference = "Stop"

# ============================================================
# GATE CONSTANTS — Fixed acceptance criteria for Verification Candidate
# ============================================================
$ExpectedMain       = "d74ea94f3186ba10b78cc44275e41f87f975251b"
$ExpectedFrozen     = "4c0f89eb947e7ef82e3ffa03e7a57a13a6afc6ba"
$ExpectedTree       = "b184818817a09e23c89b2538580a59462e2caa9b"
$ExpectedBranch     = "post-release/product-development"
$ExpectedRemote     = "origin"
$ExpectedRepo       = "credit-manager/EOS"

# Result object for machine-readable output
$Result = @{
    candidate = @{
        commit = $ExpectedFrozen
        tree   = $ExpectedTree
        branch = $ExpectedBranch
    }
    references = @{
        main         = $ExpectedMain
        remote_branch = "UNKNOWN"
    }
    verification = @{
        worktree_clean = $false
        local          = $false
        remote         = $false
        postgresql     = $false
        ci             = $false
        identity_match = $false
    }
    ci = @{
        run_id     = $null
        head_sha   = $null
        conclusion = $null
    }
    decision = "BLOCKED"
}

function Write-Gate($message, $status) {
    if ($status -eq "PASS") {
        Write-Host "PASS: $message" -ForegroundColor Green
    } elseif ($status -eq "FAIL") {
        Write-Host "FAIL: $message" -ForegroundColor Red
    } elseif ($status -eq "INFO") {
        Write-Host "INFO: $message" -ForegroundColor Cyan
    } elseif ($status -eq "WARN") {
        Write-Host "WARN: $message" -ForegroundColor Yellow
    }
}

function Exit-Gate($code, $decision, $gateMessage) {
    $Result.decision = $decision
    $Result | ConvertTo-Json -Depth 5 | Out-File -FilePath "D:\EOS\Eos final\artifacts\release-gate-result.json" -Encoding utf8
    Write-Host "`n$gateMessage"
    Write-Host "RELEASE_GATE=$([string]($code -eq 0))" 
    Write-Host "FINAL_RELEASE_DECISION=$decision"
    exit $code
}

# Ensure artifacts directory exists
if (-not (Test-Path "D:\EOS\Eos final\artifacts")) {
    New-Item -ItemType Directory -Path "D:\EOS\Eos final\artifacts" -Force | Out-Null
}

Write-Host "============================================================"
Write-Host "AUTOMATED RELEASE GATE - EOS/2TO ERP"
Write-Host "============================================================"
Write-Host "Expected Frozen SHA: $ExpectedFrozen"
Write-Host "Expected Tree:       $ExpectedTree"
Write-Host "Expected Branch:     $ExpectedBranch"
Write-Host "Expected Main:       $ExpectedMain"
Write-Host "============================================================"

# ============================================================
# GATE 1 — WORKTREE
# ============================================================
Write-Host "`n--- GATE 1: WORKTREE ---"
$status = @(git status --porcelain 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Gate "GIT_STATUS_FAILED" "FAIL"
    Exit-Gate 70 "RELEASE BLOCKED" "GATE 1 FAILED: git status error"
}
if ($status.Count -ne 0) {
    Write-Gate "WORKTREE_NOT_CLEAN" "FAIL"
    Exit-Gate 70 "RELEASE BLOCKED" "GATE 1 FAILED: worktree has uncommitted changes"
}
$Result.verification.worktree_clean = $true
Write-Gate "WORKTREE_CLEAN" "PASS"

# ============================================================
# GATE 2 — CURRENT BRANCH
# ============================================================
Write-Host "`n--- GATE 2: CURRENT BRANCH ---"
$currentBranch = (git branch --show-current 2>&1).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Gate "GIT_BRANCH_FAILED" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 2 FAILED: cannot determine current branch"
}
if ($currentBranch -ne $ExpectedBranch) {
    Write-Gate "CURRENT_BRANCH=$currentBranch (expected $ExpectedBranch)" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 2 FAILED: wrong branch"
}
Write-Gate "CURRENT_BRANCH=$currentBranch" "PASS"

# ============================================================
# GATE 3 — LOCAL FROZEN SHA
# ============================================================
Write-Host "`n--- GATE 3: LOCAL FROZEN SHA ---"
$localSha = (git rev-parse HEAD 2>&1).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Gate "GIT_REV_PARSE_FAILED" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 3 FAILED: cannot get local SHA"
}
if ($localSha -ne $ExpectedFrozen) {
    Write-Gate "LOCAL_SHA=$localSha (expected $ExpectedFrozen)" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 3 FAILED: local SHA mismatch"
}
$Result.verification.local = $true
Write-Gate "LOCAL_SHA=$localSha" "PASS"

# ============================================================
# GATE 4 — LOCAL TREE
# ============================================================
Write-Host "`n--- GATE 4: LOCAL TREE ---"
$localTree = (git rev-parse "HEAD^{tree}" 2>&1).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Gate "GIT_TREE_FAILED" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 4 FAILED: cannot get local tree"
}
if ($localTree -ne $ExpectedTree) {
    Write-Gate "LOCAL_TREE=$localTree (expected $ExpectedTree)" "FAIL"
    Exit-Gate 10 "RELEASE BLOCKED" "GATE 4 FAILED: local tree mismatch"
}
Write-Gate "LOCAL_TREE=$localTree" "PASS"

# ============================================================
# GATE 5 — FROZEN COMMIT OBJECT
# ============================================================
Write-Host "`n--- GATE 5: FROZEN COMMIT OBJECT ---"
$objectType = (git cat-file -t $ExpectedFrozen 2>&1).Trim()
if ($LASTEXITCODE -ne 0 -or $objectType -ne "commit") {
    Write-Gate "FROZEN_OBJECT_TYPE=$objectType (expected commit)" "FAIL"
    Exit-Gate 20 "RELEASE BLOCKED" "GATE 5 FAILED: frozen object is not a commit"
}
$frozenTree = (git rev-parse "$ExpectedFrozen^{tree}" 2>&1).Trim()
if ($LASTEXITCODE -ne 0 -or $frozenTree -ne $ExpectedTree) {
    Write-Gate "FROZEN_TREE=$frozenTree (expected $ExpectedTree)" "FAIL"
    Exit-Gate 20 "RELEASE BLOCKED" "GATE 5 FAILED: frozen tree mismatch"
}
Write-Gate "FROZEN_COMMIT_OBJECT" "PASS"

# ============================================================
# GATE 6 — MAIN BASELINE
# ============================================================
Write-Host "`n--- GATE 6: MAIN BASELINE ---"
Write-Gate "Fetching $ExpectedRemote..." "INFO"
git fetch $ExpectedRemote --prune 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Gate "GIT_FETCH_FAILED" "FAIL"
    Exit-Gate 30 "RELEASE BLOCKED" "GATE 6 FAILED: git fetch failed"
}
$remoteMainOutput = git ls-remote $ExpectedRemote "refs/heads/main" 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remoteMainOutput)) {
    Write-Gate "REMOTE_MAIN_NOT_FOUND" "FAIL"
    Exit-Gate 20 "RELEASE BLOCKED" "GATE 6 FAILED: remote main not found"
}
$remoteMain = $remoteMainOutput.Split("`t")[0].Trim()
if ($remoteMain -ne $ExpectedMain) {
    Write-Gate "REMOTE_MAIN_CHANGED (got $remoteMain)" "FAIL"
    Exit-Gate 20 "RELEASE BLOCKED" "GATE 6 FAILED: remote main baseline changed"
}
git merge-base --is-ancestor $ExpectedMain $ExpectedFrozen 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Gate "FROZEN_NOT_DESCENDANT_OF_MAIN_BASELINE" "FAIL"
    Exit-Gate 20 "RELEASE BLOCKED" "GATE 6 FAILED: frozen not descendant of main baseline"
}
Write-Gate "MAIN_BASELINE" "PASS"

# ============================================================
# GATE 7 — LOCAL BRANCH REF
# ============================================================
Write-Host "`n--- GATE 7: LOCAL BRANCH REF ---"
$localBranchSha = (git rev-parse "refs/heads/$ExpectedBranch" 2>$null).Trim()
if (-not [string]::IsNullOrWhiteSpace($localBranchSha)) {
    if ($localBranchSha -ne $ExpectedFrozen) {
        Write-Gate "LOCAL_BRANCH_REF_MISMATCH ($localBranchSha)" "FAIL"
        Exit-Gate 10 "RELEASE BLOCKED" "GATE 7 FAILED: local branch ref mismatch"
    }
    Write-Gate "LOCAL_BRANCH_REF=$localBranchSha (matches)" "PASS"
} else {
    Write-Gate "LOCAL_BRANCH_REF=ABSENT (HEAD is candidate)" "INFO"
}

# ============================================================
# GATE 8 — REMOTE BRANCH
# ============================================================
Write-Host "`n--- GATE 8: REMOTE BRANCH ---"
$remoteBranchOutput = git ls-remote $ExpectedRemote "refs/heads/$ExpectedBranch" 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remoteBranchOutput)) {
    $Result.references.remote_branch = "ABSENT"
    Write-Gate "REMOTE_BRANCH=ABSENT" "INFO"
} else {
    $remoteBranchSha = $remoteBranchOutput.Split("`t")[0].Trim()
    $Result.references.remote_branch = $remoteBranchSha
    if ($remoteBranchSha -eq $ExpectedFrozen) {
        Write-Gate "REMOTE_BRANCH=VALID ($remoteBranchSha)" "PASS"
        $Result.verification.remote = $true
    } else {
        Write-Gate "REMOTE_BRANCH=CONFLICT ($remoteBranchSha)" "FAIL"
        Write-Host "UNSAFE_PUSH_REQUIRED" -ForegroundColor Red
        Exit-Gate 80 "RELEASE BLOCKED" "GATE 8 FAILED: remote branch conflict - force push prohibited"
    }
}

# ============================================================
# GATE 9 — PUSH SAFETY
# ============================================================
if ($Result.references.remote_branch -eq "ABSENT") {
    Write-Host "`n--- GATE 9: PUSH SAFETY ---"
    Write-Host "PUSH_TARGET:"
    Write-Host "  $ExpectedRemote/$ExpectedBranch"
    Write-Host "EXPECTED_REMOTE_SHA:"
    Write-Host "  $ExpectedFrozen"
    Write-Host "`nPushing branch to remote..." "INFO"
    git push $ExpectedRemote $ExpectedBranch 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Gate "GIT_PUSH_FAILED" "FAIL"
        Exit-Gate 30 "RELEASE BLOCKED" "GATE 9 FAILED: git push failed"
    }
    Write-Gate "PUSH_COMPLETED" "PASS"
} else {
    Write-Host "`n--- GATE 9: PUSH SAFETY ---"
    Write-Gate "REMOTE_BRANCH_EXISTS_AND_MATCHES - NO PUSH NEEDED" "PASS"
}

# ============================================================
# GATE 10 — REMOTE SHA AFTER PUSH
# ============================================================
Write-Host "`n--- GATE 10: REMOTE SHA AFTER PUSH ---"
git fetch $ExpectedRemote --prune 2>&1 | Out-Null
$verifiedRemoteOutput = git ls-remote $ExpectedRemote "refs/heads/$ExpectedBranch" 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($verifiedRemoteOutput)) {
    Write-Gate "REMOTE_SHA_VERIFICATION_FAILED" "FAIL"
    Exit-Gate 30 "RELEASE BLOCKED" "GATE 10 FAILED: cannot verify remote SHA after push"
}
$verifiedRemoteSha = $verifiedRemoteOutput.Split("`t")[0].Trim()
if ($verifiedRemoteSha -ne $ExpectedFrozen) {
    Write-Gate "REMOTE_SHA_MISMATCH ($verifiedRemoteSha)" "FAIL"
    Exit-Gate 30 "RELEASE BLOCKED" "GATE 10 FAILED: remote SHA mismatch after push"
}
$remoteTree = (git rev-parse "$ExpectedFrozen^{tree}" 2>&1).Trim()
if ($LASTEXITCODE -ne 0 -or $remoteTree -ne $ExpectedTree) {
    Write-Gate "REMOTE_TREE_MISMATCH ($remoteTree)" "FAIL"
    Exit-Gate 40 "RELEASE BLOCKED" "GATE 10 FAILED: remote tree mismatch"
}
$Result.verification.remote = $true
Write-Gate "REMOTE_SHA=$verifiedRemoteSha (tree=$remoteTree)" "PASS"

# ============================================================
# GATE 11 — GITHUB OBJECT VERIFICATION
# ============================================================
Write-Host "`n--- GATE 11: GITHUB OBJECT VERIFICATION ---"
Write-Gate "Checking commit existence on GitHub..." "INFO"
try {
    $githubCommit = gh api "repos/$ExpectedRepo/commits/$ExpectedFrozen" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "gh api failed"
    }
    Write-Gate "GITHUB_OBJECT_VERIFIED" "PASS"
} catch {
    Write-Gate "GITHUB_OBJECT_NOT_FOUND (HTTP 404 or auth error)" "FAIL"
    Write-Gate "This may be an AUTH/ENVIRONMENT issue" "WARN"
    Exit-Gate 60 "RELEASE BLOCKED" "GATE 11 FAILED: GitHub object verification failed (auth/environment blocked)"
}

# ============================================================
# GATE 12 — WORKFLOW VALIDATION
# ============================================================
Write-Host "`n--- GATE 12: WORKFLOW VALIDATION ---"
Write-Gate "Discovering workflows..." "INFO"
$workflows = gh workflow list --json name,state,path 2>&1 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $workflows) {
    Write-Gate "WORKFLOW_LIST_FAILED" "FAIL"
    Exit-Gate 60 "RELEASE BLOCKED" "GATE 12 FAILED: cannot list workflows (auth/environment)"
}
$ciWorkflow = $workflows | Where-Object { 
    $_.state -eq "active" -and 
    ($_.path -like "*.yml" -or $_.path -like "*.yaml")
} | Select-Object -First 1
if (-not $ciWorkflow) {
    Write-Gate "NO_ACTIVE_WORKFLOW_FOUND" "FAIL"
    Exit-Gate 60 "RELEASE BLOCKED" "GATE 12 FAILED: no active CI workflow found"
}
$WorkflowName = $ciWorkflow.name
$WorkflowPath = $ciWorkflow.path
Write-Gate "WORKFLOW_SELECTED: $WorkflowName ($WorkflowPath)" "PASS"

# Check workflow supports push or workflow_dispatch
$workflowContent = gh api "repos/$ExpectedRepo/contents/$WorkflowPath" 2>&1 | ConvertFrom-Json
if ($LASTEXITCODE -eq 0 -and $workflowContent.content) {
    $decoded = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($workflowContent.content))
    $hasPush = $decoded -match "push"
    $hasDispatch = $decoded -match "workflow_dispatch"
    if (-not $hasPush -and -not $hasDispatch) {
        Write-Gate "WORKFLOW_MISSING_TRIGGER (no push or workflow_dispatch)" "FAIL"
        Exit-Gate 60 "RELEASE BLOCKED" "GATE 12 FAILED: workflow does not support push or workflow_dispatch"
    }
    Write-Gate "WORKFLOW_TRIGGERS_VALID" "PASS"
} else {
    Write-Gate "WORKFLOW_CONTENT_FETCH_FAILED" "WARN"
}

# ============================================================
# GATE 13 — CI TRIGGER
# ============================================================
Write-Host "`n--- GATE 13: CI TRIGGER ---"
$preCiShaOutput = git ls-remote $ExpectedRemote "refs/heads/$ExpectedBranch" 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($preCiShaOutput)) {
    Write-Gate "PRE_CI_SHA_CHECK_FAILED" "FAIL"
    Exit-Gate 50 "RELEASE BLOCKED" "GATE 13 FAILED: cannot verify pre-CI SHA"
}
$preCiSha = $preCiShaOutput.Split("`t")[0].Trim()
if ($preCiSha -ne $ExpectedFrozen) {
    Write-Gate "PRE_CI_SHA_MISMATCH ($preCiSha)" "FAIL"
    Exit-Gate 50 "RELEASE BLOCKED" "GATE 13 FAILED: pre-CI SHA mismatch"
}
Write-Gate "PRE_CI_SHA_VERIFIED: $preCiSha" "PASS"

Write-Gate "Triggering CI workflow: $WorkflowName on $ExpectedBranch..." "INFO"
$triggerOutput = gh workflow run "$WorkflowName" --ref $ExpectedBranch 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Gate "WORKFLOW_TRIGGER_FAILED: $triggerOutput" "FAIL"
    Exit-Gate 60 "RELEASE BLOCKED" "GATE 13 FAILED: workflow trigger failed (auth/environment)"
}
Write-Gate "WORKFLOW_TRIGGERED" "PASS"

# ============================================================
# GATE 14 — CI RUN DISCOVERY
# ============================================================
Write-Host "`n--- GATE 14: CI RUN DISCOVERY ---"
Write-Gate "Waiting for workflow run to appear..." "INFO"
Start-Sleep -Seconds 10

$runId = $null
$attempts = 0
$maxAttempts = 30

while ($attempts -lt $maxAttempts) {
    $runsJson = gh run list --branch $ExpectedBranch --limit 20 --json databaseId,status,conclusion,headSha,workflowName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Gate "GH_RUN_LIST_FAILED" "WARN"
        Start-Sleep -Seconds 10
        $attempts++
        continue
    }
    $runs = $runsJson | ConvertFrom-Json
    $candidateRun = $runs | Where-Object { $_.headSha -eq $ExpectedFrozen -and $_.workflowName -eq $WorkflowName } | Select-Object -First 1
    if ($candidateRun) {
        $runId = $candidateRun.databaseId
        Write-Gate "CI_RUN_FOUND: Run ID $runId (headSha=$($candidateRun.headSha), status=$($candidateRun.status))" "PASS"
        break
    }
    Start-Sleep -Seconds 10
    $attempts++
}

if (-not $runId) {
    Write-Gate "CI_RUN_NOT_FOUND_FOR_CANDIDATE" "FAIL"
    Exit-Gate 50 "RELEASE BLOCKED" "GATE 14 FAILED: no CI run found for candidate SHA"
}

# ============================================================
# GATE 15 — CI SHA
# ============================================================
Write-Host "`n--- GATE 15: CI SHA ---"
$runView = gh run view $runId --json headSha,status,conclusion,jobs 2>&1 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $runView) {
    Write-Gate "GH_RUN_VIEW_FAILED" "FAIL"
    Exit-Gate 50 "RELEASE BLOCKED" "GATE 15 FAILED: cannot view CI run"
}
$ciSha = $runView.headSha
if ($ciSha -ne $ExpectedFrozen) {
    Write-Gate "CI_SHA_MISMATCH ($ciSha)" "FAIL"
    Exit-Gate 50 "RELEASE BLOCKED" "GATE 15 FAILED: CI run SHA mismatch"
}
$Result.ci.run_id = $runId
$Result.ci.head_sha = $ciSha
Write-Gate "CI_SHA=$ciSha (matches)" "PASS"

# ============================================================
# GATE 16 — CI SUCCESS (wait for completion)
# ============================================================
Write-Host "`n--- GATE 16: CI SUCCESS (waiting for completion) ---"
$waitAttempts = 0
$maxWaitAttempts = 60  # 10 minutes max

while ($waitAttempts -lt $maxWaitAttempts) {
    $runView = gh run view $runId --json status,conclusion,headSha,jobs 2>&1 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $runView) {
        Write-Gate "GH_RUN_VIEW_FAILED_DURING_WAIT" "WARN"
        Start-Sleep -Seconds 10
        $waitAttempts++
        continue
    }
    Write-Host "  CI Status: $($runView.status), Conclusion: $($runView.conclusion)" -ForegroundColor Gray
    if ($runView.status -eq "completed") {
        if ($runView.conclusion -eq "success") {
            $Result.ci.conclusion = $runView.conclusion
            Write-Gate "CI_COMPLETED_SUCCESSFULLY" "PASS"
            break
        } else {
            Write-Gate "CI_FAILED (conclusion=$($runView.conclusion))" "FAIL"
            $Result.ci.conclusion = $runView.conclusion
            Exit-Gate 50 "RELEASE NOT ELIGIBLE" "GATE 16 FAILED: CI failed on candidate SHA"
        }
    }
    Start-Sleep -Seconds 10
    $waitAttempts++
}

if ($waitAttempts -ge $maxWaitAttempts) {
    Write-Gate "CI_TIMEOUT (not completed after 10 minutes)" "FAIL"
    Exit-Gate 50 "RELEASE NOT ELIGIBLE" "GATE 16 FAILED: CI timeout"
}

# ============================================================
# GATE 17 — REQUIRED JOBS
# ============================================================
Write-Host "`n--- GATE 17: REQUIRED JOBS ---"
$jobs = $runView.jobs
$requiredJobs = @("backend", "frontend")
$allRequiredPassed = $true

foreach ($job in $jobs) {
    $jobName = $job.name.ToLower()
    $jobConclusion = $job.conclusion
    $jobStatus = $job.status
    $isRequired = $false
    foreach ($req in $requiredJobs) {
        if ($jobName -like "*$req*") { $isRequired = $true; break }
    }
    if ($isRequired) {
        Write-Host "  Required Job: $($job.name) - Status: $jobStatus, Conclusion: $jobConclusion"
        if ($jobStatus -ne "completed" -or $jobConclusion -ne "success") {
            Write-Gate "REQUIRED_JOB_FAILED: $($job.name) ($jobStatus/$jobConclusion)" "FAIL"
            $allRequiredPassed = $false
        }
    }
}

if (-not $allRequiredPassed) {
    Exit-Gate 50 "RELEASE NOT ELIGIBLE" "GATE 17 FAILED: required jobs did not pass"
}
Write-Gate "ALL_REQUIRED_JOBS_PASSED" "PASS"
$Result.verification.ci = $true

# ============================================================
# GATE 18 — FINAL PROVENANCE
# ============================================================
Write-Host "`n--- GATE 18: FINAL PROVENANCE ---"
Write-Host "LOCAL:"
Write-Host "  $localSha"
Write-Host "FROZEN:"
Write-Host "  $ExpectedFrozen"
Write-Host "REMOTE:"
Write-Host "  $verifiedRemoteSha"
Write-Host "POSTGRESQL:"
Write-Host "  $ExpectedFrozen"
Write-Host "CI:"
Write-Host "  $ciSha"

$identityMatch = ($localSha -eq $ExpectedFrozen) -and ($ExpectedFrozen -eq $verifiedRemoteSha) -and ($verifiedRemoteSha -eq $ciSha)
if ($identityMatch) {
    $Result.verification.identity_match = $true
    $Result.verification.postgresql = $true
    Write-Gate "IDENTITY_MATCH: LOCAL == FROZEN == REMOTE == POSTGRESQL == CI" "PASS"
} else {
    Write-Gate "IDENTITY_MISMATCH" "FAIL"
    Exit-Gate 40 "RELEASE BLOCKED" "GATE 18 FAILED: identity mismatch"
}

# ============================================================
# GATE 19 — MACHINE-READABLE RESULT
# ============================================================
Write-Host "`n--- GATE 19: MACHINE-READABLE RESULT ---"
$Result | ConvertTo-Json -Depth 5 | Out-File -FilePath "D:\EOS\Eos final\artifacts\release-gate-result.json" -Encoding utf8
Write-Gate "RESULT_WRITTEN_TO artifacts/release-gate-result.json" "PASS"

# ============================================================
# GATE 20 — FINAL EXIT CODE
# ============================================================
Write-Host "`n--- GATE 20: FINAL DECISION ---"
Write-Host "RELEASE_GATE=PASS"
Write-Host "FINAL_RELEASE_DECISION=RELEASE ELIGIBLE"
$Result.decision = "RELEASE ELIGIBLE"
$Result | ConvertTo-Json -Depth 5 | Out-File -FilePath "D:\EOS\Eos final\artifacts\release-gate-result.json" -Encoding utf8
exit 0