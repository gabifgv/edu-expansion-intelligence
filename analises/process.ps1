$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$cidadeNomes = @{
    '3509502' = 'Campinas'
    '3525904' = 'Jundiai'
    '3538709' = 'Piracicaba'
    '3552205' = 'Sorocaba'
}

# CARGOS - Top 30 por cidade
$cargos = Get-Content 'C:\edu-expansion-intelligence\analises\out\q4_cargos.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$out = "## Cargos - Top 30 elegiveis por cidade`n`n"

foreach ($id in '3509502','3525904','3538709','3552205') {
    $nome = $cidadeNomes[$id]
    $rows = $cargos | Where-Object { $_.id_municipio -eq $id } | Sort-Object { [int]$_.eleg_2022 } -Descending | Select-Object -First 30
    $out += "### $nome`n`n"
    $hdr = "| Cargo | V2020 | S2020 | V2021 | S2021 | V2022 | S2022 | Eleg2022 | DV_pct | DE_pct |`n"
    $out += $hdr
    $out += "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|`n"
    foreach ($r in $rows) {
        $cargo = $r.descricao_cargo -replace '\|', '/'
        $v20 = if ($r.vinc_2020) { [int]$r.vinc_2020 } else { 0 }
        $v21 = if ($r.vinc_2021) { [int]$r.vinc_2021 } else { 0 }
        $v22 = if ($r.vinc_2022) { [int]$r.vinc_2022 } else { 0 }
        $s20 = if ($r.sal_2020) { [math]::Round([double]$r.sal_2020, 0) } else { '-' }
        $s21 = if ($r.sal_2021) { [math]::Round([double]$r.sal_2021, 0) } else { '-' }
        $s22 = if ($r.sal_2022) { [math]::Round([double]$r.sal_2022, 0) } else { '-' }
        $eleg22 = [int]$r.eleg_2022
        $dv = if ($r.delta_vinc_pct) { $r.delta_vinc_pct } else { '-' }
        $de = if ($r.delta_eleg_pct) { $r.delta_eleg_pct } else { '-' }
        $out += "| $cargo | $v20 | $s20 | $v21 | $s21 | $v22 | $s22 | $eleg22 | $dv | $de |`n"
    }
    $out += "`n"
}

[System.IO.File]::WriteAllText('C:\edu-expansion-intelligence\analises\out\report_cargos.md', $out, [System.Text.UTF8Encoding]::new($false))
Write-Output "Cargos OK"

# CURSOS - Top 20 por concluintes 2024
$cursos = Get-Content 'C:\edu-expansion-intelligence\analises\out\q6_cursos.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$outc = "## Cursos - Top 20 por concluintes 2024 por cidade`n`n"

foreach ($id in '3509502','3525904','3538709','3552205') {
    $nome = $cidadeNomes[$id]
    $rows = $cursos | Where-Object { $_.id_municipio -eq $id } | Sort-Object { [int]$_.conc_2024 } -Descending | Select-Object -First 20
    $outc += "### $nome`n`n"
    $outc += "| Area especifica | Area detalhada | C2020 | C2021 | C2022 | C2023 | C2024 | M2024 | I2024 | D_pct |`n"
    $outc += "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|`n"
    foreach ($r in $rows) {
        $ae = $r.nome_area_especifica -replace '\|', '/'
        $ad = $r.nome_area_detalhada -replace '\|', '/'
        $c20 = [int]$r.conc_2020
        $c21 = [int]$r.conc_2021
        $c22 = [int]$r.conc_2022
        $c23 = [int]$r.conc_2023
        $c24 = [int]$r.conc_2024
        $m24 = [int]$r.matr_2024
        $i24 = [int]$r.ing_2024
        $dc = if ($r.delta_conc_pct) { $r.delta_conc_pct } else { '-' }
        $outc += "| $ae | $ad | $c20 | $c21 | $c22 | $c23 | $c24 | $m24 | $i24 | $dc |`n"
    }
    $outc += "`n"
}

[System.IO.File]::WriteAllText('C:\edu-expansion-intelligence\analises\out\report_cursos.md', $outc, [System.Text.UTF8Encoding]::new($false))
Write-Output "Cursos OK"

# CURSOS - Top 15 maior crescimento (com cap 2024 >= 30)
$outg = "## Cursos - Top 15 maior crescimento 2020-2024 (cap 2024 >= 30 concluintes)`n`n"
foreach ($id in '3509502','3525904','3538709','3552205') {
    $nome = $cidadeNomes[$id]
    $rows = $cursos | Where-Object { $_.id_municipio -eq $id -and [int]$_.conc_2024 -ge 30 -and $_.delta_conc_pct -ne $null } | Sort-Object { [double]$_.delta_conc_pct } -Descending | Select-Object -First 15
    $outg += "### $nome`n`n"
    $outg += "| Area especifica | Area detalhada | C2020 | C2024 | Delta_pct |`n"
    $outg += "|---|---|--:|--:|--:|`n"
    foreach ($r in $rows) {
        $ae = $r.nome_area_especifica -replace '\|', '/'
        $ad = $r.nome_area_detalhada -replace '\|', '/'
        $outg += "| $ae | $ad | $($r.conc_2020) | $($r.conc_2024) | $($r.delta_conc_pct) |`n"
    }
    $outg += "`n"
}
[System.IO.File]::WriteAllText('C:\edu-expansion-intelligence\analises\out\report_cursos_crescimento.md', $outg, [System.Text.UTF8Encoding]::new($false))
Write-Output "Crescimento OK"
