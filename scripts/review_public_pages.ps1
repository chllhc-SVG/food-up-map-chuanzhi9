param([int]$Limit=293)
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$catalog=Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $project 'docs/fuzhou-catalog.json') | ConvertFrom-Json
$cache=Join-Path $project '.local/fz-pages'
[void][IO.Directory]::CreateDirectory($cache)
$seen=0
foreach($film in ($catalog|Select-Object -First $Limit)){
    if ($film.bvid -cnotmatch '^BV[0-9A-Za-z]{10}$'){throw 'Invalid BV in catalog'}
    $destination=Join-Path $cache ($film.bvid+'.json')
    if (Test-Path -LiteralPath $destination){continue}
    $url='https://www.bilibili.com/video/'+$film.bvid+'/'
    $page=Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri $url
    $meta=[regex]::Match($page.Content,'(?is)<meta\s+(?=[^>]*\bname="description")(?=[^>]*\bcontent="([^"]*)")[^>]+>')
    if(!$meta.Success){Write-Output ('Metadata unavailable at '+$film.bvid+'; stopping.');break}
    $value=[System.Net.WebUtility]::HtmlDecode($meta.Groups[1].Value)
    if (!$value.Contains('视频作者 酷酷的珊文鱼')){Write-Output ('Author could not be confirmed at '+$film.bvid+'; stopping.');break}
    $excerpt=[regex]::Split($value,'[,，]\s*视频播放量',2)[0].Trim()
    if ($excerpt.Length -gt 400){$excerpt=$excerpt.Substring(0,400)}
    $row=[ordered]@{bvid=$film.bvid;title=$film.title;description=$excerpt;url=$url}
    [IO.File]::WriteAllText($destination,($row|ConvertTo-Json -Compress))
    $seen++
    if (($seen % 20) -eq 0){Write-Output ("Reviewed "+$seen+" new public descriptions.")}
    Start-Sleep -Milliseconds 1250
}
Write-Output ("Finished: "+$seen+" new public descriptions.")
