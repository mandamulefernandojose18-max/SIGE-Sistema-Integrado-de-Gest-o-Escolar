# SIGE - Assistente de scanner (Windows / WIA)
# Liga o botão «Digitalizar com o scanner» do SIGE ao scanner deste computador.
# Como usar: botão direito neste ficheiro > «Executar com o PowerShell» e deixe a janela aberta enquanto corrige provas.
# Só aceita pedidos vindos de https://sigesaas.duckdns.org (e do próprio computador). Não envia nada para a internet:
# devolve o PDF digitalizado à página do SIGE que o pediu.
param([int]$Porta = 47811, [switch]$Teste)

$ErrorActionPreference = 'Stop'
$Origens = @('https://sigesaas.duckdns.org', 'http://localhost:8000', 'http://127.0.0.1:8000')
$FmtJpeg = '{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}'

function Ajustar($props, $id, $valor) {
    try { $props.Item("$id").Value = $valor } catch { }
}

function Digitalizar([int]$dpi) {
    $gestor = New-Object -ComObject WIA.DeviceManager
    if ($gestor.DeviceInfos.Count -lt 1) { throw 'Nenhum scanner ligado. Ligue o scanner e tente de novo.' }
    $disp = $gestor.DeviceInfos.Item(1).Connect()
    # alimentador automático de folhas (ADF), todas as páginas: 3088 = Document Handling Select (1 = alimentador), 3096 = Pages (0 = todas)
    Ajustar $disp.Properties 3088 1
    Ajustar $disp.Properties 3096 0
    $feeder = $false; try { $feeder = (($disp.Properties.Item('3086').Value -band 1) -eq 1) } catch { }
    $ficheiros = @()
    $pasta = Join-Path $env:TEMP ('sige_scan_' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $pasta | Out-Null
    for ($i = 1; $i -le 400; $i++) {
        $item = $disp.Items.Item(1)
        Ajustar $item.Properties 6146 1             # cor (tinta azul/preta distingue-se)
        Ajustar $item.Properties 6147 $dpi
        Ajustar $item.Properties 6148 $dpi
        Ajustar $item.Properties 6149 0
        Ajustar $item.Properties 6150 0
        Ajustar $item.Properties 6151 [int](8.27 * $dpi)
        Ajustar $item.Properties 6152 [int](11.69 * $dpi)
        try {
            $img = $item.Transfer($FmtJpeg)
        } catch {
            $cod = ($_.Exception.InnerException, $_.Exception | Where-Object { $_ } | Select-Object -First 1).HResult
            if ($i -gt 1 -or $cod -eq -2145320957) { break }      # 0x80210003 = sem mais papel no alimentador
            throw
        }
        $f = Join-Path $pasta ('p{0:D4}.jpg' -f $i)
        $img.SaveFile($f)
        $ficheiros += $f
        if (-not $feeder) { break }            # vidro (sem alimentador): só uma página
    }
    if ($ficheiros.Count -eq 0) { throw 'O scanner não devolveu nenhuma folha. Coloque as folhas no alimentador.' }
    return , @($pasta, $ficheiros)
}

function Criar-Pdf([string[]]$jpgs) {
    Add-Type -AssemblyName System.Drawing
    $ms = New-Object IO.MemoryStream
    $enc = [Text.Encoding]::ASCII
    $offs = New-Object System.Collections.ArrayList
    $esc = { param($s) $b = $enc.GetBytes($s); $ms.Write($b, 0, $b.Length) }
    & $esc "%PDF-1.4`n"
    $n = $jpgs.Count
    $filhos = (0..($n - 1) | ForEach-Object { '{0} 0 R' -f (3 + 3 * $_) }) -join ' '
    $objeto = { param($id, $corpo) [void]$offs.Add(@($id, $ms.Position)); & $esc ("$id 0 obj`n$corpo`nendobj`n") }
    & $objeto 1 '<< /Type /Catalog /Pages 2 0 R >>'
    & $objeto 2 ("<< /Type /Pages /Kids [$filhos] /Count $n >>")
    for ($i = 0; $i -lt $n; $i++) {
        $idp = 3 + 3 * $i; $idi = $idp + 1; $idc = $idp + 2
        $bytes = [IO.File]::ReadAllBytes($jpgs[$i])
        $im = [System.Drawing.Image]::FromFile($jpgs[$i]); $w = $im.Width; $h = $im.Height; $im.Dispose()
        & $objeto $idp "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im0 $idi 0 R >> >> /Contents $idc 0 R >>"
        [void]$offs.Add(@($idi, $ms.Position))
        & $esc "$idi 0 obj`n<< /Type /XObject /Subtype /Image /Width $w /Height $h /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length $($bytes.Length) >>`nstream`n"
        $ms.Write($bytes, 0, $bytes.Length)
        & $esc "`nendstream`nendobj`n"
        $cont = 'q 595.28 0 0 841.89 0 0 cm /Im0 Do Q'
        & $objeto $idc "<< /Length $($cont.Length) >>`nstream`n$cont`nendstream"
    }
    $xref = $ms.Position
    $total = 3 + 3 * $n
    & $esc ("xref`n0 $total`n0000000000 65535 f `n")
    foreach ($o in ($offs | Sort-Object { $_[0] })) { & $esc ('{0:D10} 00000 n `n' -f [int64]$o[1]) }
    & $esc ("trailer`n<< /Size $total /Root 1 0 R >>`nstartxref`n$xref`n%%EOF`n")
    return , $ms.ToArray()
}

function Cabecalhos($ctx) {
    $orig = $ctx.Request.Headers['Origin']
    if ($orig -and ($Origens -contains $orig)) {
        $ctx.Response.Headers['Access-Control-Allow-Origin'] = $orig
        $ctx.Response.Headers['Vary'] = 'Origin'
        $ctx.Response.Headers['Access-Control-Allow-Private-Network'] = 'true'
        $ctx.Response.Headers['Access-Control-Allow-Headers'] = '*'
    }
}

if ($Teste) { return }
$ouvinte = New-Object System.Net.HttpListener
$ouvinte.Prefixes.Add("http://127.0.0.1:$Porta/")
$ouvinte.Start()
Write-Host "SIGE scanner pronto (127.0.0.1:$Porta). Deixe esta janela aberta. Ctrl+C para sair."
while ($ouvinte.IsListening) {
    $ctx = $ouvinte.GetContext()
    try {
        Cabecalhos $ctx
        $orig = $ctx.Request.Headers['Origin']
        if ($orig -and -not ($Origens -contains $orig)) { $ctx.Response.StatusCode = 403; $ctx.Response.Close(); continue }
        $caminho = $ctx.Request.Url.AbsolutePath
        if ($ctx.Request.HttpMethod -eq 'OPTIONS') { $ctx.Response.StatusCode = 204 }
        elseif ($caminho -eq '/estado') {
            $b = [Text.Encoding]::UTF8.GetBytes('{"pronto":true}')
            $ctx.Response.ContentType = 'application/json'; $ctx.Response.OutputStream.Write($b, 0, $b.Length)
        }
        elseif ($caminho -eq '/digitalizar') {
            $dpi = 200; try { $dpi = [int]$ctx.Request.QueryString['dpi'] } catch { }
            if ($dpi -lt 150 -or $dpi -gt 300) { $dpi = 200 }
            $r = Digitalizar $dpi
            $pdf = Criar-Pdf ([string[]]$r[1])
            Remove-Item -Recurse -Force $r[0] -ErrorAction SilentlyContinue
            $ctx.Response.ContentType = 'application/pdf'
            $ctx.Response.ContentLength64 = $pdf.Length
            $ctx.Response.OutputStream.Write($pdf, 0, $pdf.Length)
        }
        else { $ctx.Response.StatusCode = 404 }
    } catch {
        $ctx.Response.StatusCode = 500
        $b = [Text.Encoding]::UTF8.GetBytes((@{ erro = $_.Exception.Message } | ConvertTo-Json -Compress))
        $ctx.Response.ContentType = 'application/json'; $ctx.Response.OutputStream.Write($b, 0, $b.Length)
    } finally { try { $ctx.Response.Close() } catch { } }
}
