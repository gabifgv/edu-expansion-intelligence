$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$cidades = 'Campinas','Jundiai','Piracicaba','Sorocaba'

foreach ($c in $cidades) {
    $d = Get-Content "C:\edu-expansion-intelligence\analises\out\dashboard_$c.json" -Raw -Encoding Unicode | ConvertFrom-Json

    Write-Output ""
    Write-Output "================================================================"
    Write-Output "## $c"
    Write-Output "================================================================"

    Write-Output ""
    Write-Output "### Perfil rows (vs UF SP):"
    $d.perfil.rows | ForEach-Object { Write-Output "  $($_.metrica): cidade=$($_.cidade) uf=$($_.uf) delta=$($_.delta_pct)% status=$($_.status)" }

    Write-Output ""
    Write-Output "### Top 12 setores (por_setor) ordenados por elegiveis:"
    $d.mercado_trabalho.por_setor | Sort-Object { [int]$_.elegiveis } -Descending | Select-Object -First 12 | ForEach-Object {
        Write-Output ("  [{0,6}] eleg | total={1,7} | sal_pond={2,7} | pct_eleg={3,5}% | {4}" -f $_.elegiveis, $_.total_vinculos, $_.sal_pond, $_.pct_eleg, $_.descricao_subsetor)
    }

    Write-Output ""
    Write-Output "### Top 20 cargos (por_cargo) por elegiveis:"
    $d.mercado_trabalho.por_cargo | Sort-Object { [int]$_.elegiveis } -Descending | Select-Object -First 20 | ForEach-Object {
        Write-Output ("  [{0,6}] eleg | sal={1,7} | total={2,6} | {3}" -f $_.elegiveis, $_.sal_pond, $_.total_vinculos, $_.descricao_cargo)
    }

    Write-Output ""
    Write-Output "### Pipeline cursos_alta (top 10):"
    if ($d.pipeline.cursos_alta) {
        $d.pipeline.cursos_alta | Select-Object -First 10 | ForEach-Object {
            $props = $_.PSObject.Properties.Name -join '|'
            Write-Output "  $($_ | ConvertTo-Json -Compress -Depth 3)"
        }
    } else { Write-Output "  (vazio)" }

    Write-Output ""
    Write-Output "### Pipeline areas_alta (top 10):"
    if ($d.pipeline.areas_alta) {
        $d.pipeline.areas_alta | Select-Object -First 10 | ForEach-Object {
            Write-Output "  $($_ | ConvertTo-Json -Compress -Depth 3)"
        }
    } else { Write-Output "  (vazio)" }

    Write-Output ""
    Write-Output "### Pipeline top_ies (top 10):"
    if ($d.pipeline.top_ies) {
        $d.pipeline.top_ies | Select-Object -First 10 | ForEach-Object {
            Write-Output "  $($_ | ConvertTo-Json -Compress -Depth 3)"
        }
    } else { Write-Output "  (vazio)" }

    Write-Output ""
    Write-Output "### Score (linha desta cidade):"
    $row = $d.score.cidades | Where-Object { $_.nm -match "^$c" } | Select-Object -First 1
    if ($row) {
        Write-Output "  D1=$($row.D1) D2=$($row.D2) D3=$($row.D3) D4=$($row.D4) sal=$($row.sal) vinc=$($row.vinc) tsup=$($row.tsup) idhm=$($row.idhm) cresc=$($row.cresc)"
    }

    Write-Output ""
    Write-Output "### Estab serie (ultimos 5 anos):"
    if ($d.mercado_trabalho.estab_serie) {
        $d.mercado_trabalho.estab_serie | Sort-Object ano | ForEach-Object {
            Write-Output "  ano=$($_.ano) estabs=$($_.estabs) vinc_ativos=$($_.vinc_ativos)"
        }
    }
}
