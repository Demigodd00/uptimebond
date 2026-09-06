param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\docs\assets\uptimebond\uptimebond-logo.png")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$size = 1024
$scale = $size / 64
$bitmap = [System.Drawing.Bitmap]::new(
    $size,
    $size,
    [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$backgroundPath = [System.Drawing.Drawing2D.GraphicsPath]::new()
$backgroundBrush = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml("#091512"))
$pulsePen = [System.Drawing.Pen]::new(
    [System.Drawing.ColorTranslator]::FromHtml("#91f2bd"),
    6 * $scale
)

try {
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    $diameter = 32 * $scale
    $backgroundPath.AddArc(0, 0, $diameter, $diameter, 180, 90)
    $backgroundPath.AddArc($size - $diameter, 0, $diameter, $diameter, 270, 90)
    $backgroundPath.AddArc($size - $diameter, $size - $diameter, $diameter, $diameter, 0, 90)
    $backgroundPath.AddArc(0, $size - $diameter, $diameter, $diameter, 90, 90)
    $backgroundPath.CloseFigure()
    $graphics.FillPath($backgroundBrush, $backgroundPath)

    $pulsePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pulsePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pulsePen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $points = [System.Drawing.PointF[]]@(
        [System.Drawing.PointF]::new(13 * $scale, 35 * $scale),
        [System.Drawing.PointF]::new(23 * $scale, 35 * $scale),
        [System.Drawing.PointF]::new(28 * $scale, 20 * $scale),
        [System.Drawing.PointF]::new(36 * $scale, 48 * $scale),
        [System.Drawing.PointF]::new(42 * $scale, 30 * $scale),
        [System.Drawing.PointF]::new(46 * $scale, 35 * $scale),
        [System.Drawing.PointF]::new(51 * $scale, 35 * $scale)
    )
    $graphics.DrawLines($pulsePen, $points)

    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
    [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null
    $bitmap.Save($resolvedOutput, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $resolvedOutput
}
finally {
    $pulsePen.Dispose()
    $backgroundBrush.Dispose()
    $backgroundPath.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}
