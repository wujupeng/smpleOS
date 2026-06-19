$base = "C:\Users\DELL\Documents\dev\smpleOS\aeroforge-x\services"
$files = Get-ChildItem -Path $base -Recurse -Filter "*.py" |
    Where-Object { (Get-Content $_.FullName -Raw) -match 'def __init__\(self, repo=None\) -> None:\r?\n(\s+)self\._repo = repo\r?\ndef __init__\(self, repo=None\) -> None:' }

$fixed = 0
foreach ($f in $files) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8
    $pattern = '(    def __init__\(self, repo=None\) -> None:\r?\n        self\._repo = repo\r?\n)def __init__\(self, repo=None\) -> None:\r?\n'
    $replacement = '$1'
    $newContent = $content -replace $pattern, $replacement
    if ($newContent -ne $content) {
        [System.IO.File]::WriteAllText($f.FullName, $newContent)
        $fixed++
        Write-Host "Fixed: $($f.FullName)"
    }
}
Write-Host "`nTotal fixed: $fixed"