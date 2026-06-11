$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$cidades = 'Campinas','Jundiai','Piracicaba','Sorocaba'

foreach ($c in $cidades) {
    $d = Get-Content "C:\edu-expansion-intelligence\analises\out\dashboard_$c.json" -Raw -Encoding Unicode | ConvertFrom-Json

    Write-Output ""
    Write-Output "######## $c ########"
    Write-Output ""
    Write-Output "TOP 8 SETORES por eleg:"
    $d.mercado_trabalho.por_setor | Sort-Object { [int]$_.eleg } -Descending | Select-Object -First 8 | ForEach-Object {
        Write-Output ("  eleg={0,5} | pct={1,5}% | sal_eleg={2,7} | vinc={3,6} | sal_pond={4,6} | estabs={5,5} | {6}" -f $_.eleg, $_.pct_eleg, $_.sal_eleg, $_.vinculos, $_.sal_medio, $_.estabs, $_.setor)
    }

    Write-Output ""
    Write-Output "TOP 15 CARGOS por eleg:"
    $d.mercado_trabalho.por_cargo | Sort-Object { [int]$_.eleg } -Descending | Select-Object -First 15 | ForEach-Object {
        Write-Output ("  eleg={0,5} | pct={1,5}% | sal_eleg={2,7} | vinc={3,6} | sal_pond={4,6} | {5}" -f $_.eleg, $_.pct_eleg, $_.sal_eleg, $_.vinculos, $_.sal_medio, $_.cargo)
    }
}
