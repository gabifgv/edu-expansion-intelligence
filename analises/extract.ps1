$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$cidades = 'Campinas','Jundiai','Piracicaba','Sorocaba'
$resumo = @{}

foreach ($c in $cidades) {
    $d = Get-Content "C:\edu-expansion-intelligence\analises\out\dashboard_$c.json" -Raw -Encoding Unicode | ConvertFrom-Json
    $resumo[$c] = $d
}

# Salva tudo num JSON ASCII pra inspecao
$resumo | ConvertTo-Json -Depth 20 | Out-File -FilePath 'C:\edu-expansion-intelligence\analises\out\all_cities.json' -Encoding utf8

# Sumario de KPIs principais
Write-Output ""
Write-Output "==== KPIs MT (mercado_trabalho.kpis) ===="
foreach ($c in $cidades) {
    Write-Output ""
    Write-Output "## $c (ano=$($resumo[$c].ano_emp), pop=$($resumo[$c].perfil.populacao))"
    $kpis = $resumo[$c].mercado_trabalho.kpis
    $kpis.PSObject.Properties | ForEach-Object { Write-Output "  $($_.Name): $($_.Value)" }
}

Write-Output ""
Write-Output "==== Pipeline KPIs ===="
foreach ($c in $cidades) {
    Write-Output ""
    Write-Output "## $c"
    $k = $resumo[$c].pipeline.kpis
    $k.PSObject.Properties | ForEach-Object { Write-Output "  $($_.Name): $($_.Value)" }
}

Write-Output ""
Write-Output "==== Score por cidade ===="
foreach ($c in $cidades) {
    Write-Output ""
    Write-Output "## $c"
    # score.cidades eh lista do estado SP - acha a cidade
    $row = $resumo[$c].score.cidades | Where-Object { $_.nome -eq $c -or $_.cidade -eq $c } | Select-Object -First 1
    if ($row) {
        $row.PSObject.Properties | ForEach-Object { Write-Output "  $($_.Name): $($_.Value)" }
    } else {
        Write-Output "  (nao achei - keys da primeira linha:)"
        $resumo[$c].score.cidades[0].PSObject.Properties.Name | ForEach-Object { Write-Output "    $_" }
    }
}
