# 查桌寵視窗現在在哪：印出視窗位置、是否顯示、螢幕與可用範圍（扣掉工作列）。
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File scripts/where-is-pet.ps1
# 只讀不改；「桌寵不見了」時先跑這支，看視窗是不是落在工作列或螢幕外。
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class PetWin {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    public struct RECT { public int L, T, R, B; }
}
"@
Add-Type -AssemblyName System.Windows.Forms

$lock = Join-Path $env:USERPROFILE ".terminalpet\pet.lock"
if (-not (Test-Path $lock)) { "找不到 $lock：桌寵沒有在執行"; exit 0 }
$petPid = [uint32](Get-Content $lock -TotalCount 1)
if (-not (Get-Process -Id $petPid -ErrorAction SilentlyContinue)) { "pet.lock 記的程式 $petPid 已不在：桌寵沒有在執行"; exit 0 }
"桌寵程式：PID $petPid"

$found = New-Object System.Collections.ArrayList
[void][PetWin]::EnumWindows({
    param($h, $l)
    $p = 0
    [void][PetWin]::GetWindowThreadProcessId($h, [ref]$p)
    $cls = New-Object Text.StringBuilder 256
    [void][PetWin]::GetClassName($h, $cls, 256)
    # 桌寵主視窗是 Qt 的 Tool 視窗；排除提示框（ToolTip）等其他視窗
    if ($p -eq $petPid -and $cls.ToString() -match 'QWindowToolSaveBits$') {
        $r = New-Object PetWin+RECT
        [void][PetWin]::GetWindowRect($h, [ref]$r)
        [void]$found.Add([pscustomobject]@{ Visible = [PetWin]::IsWindowVisible($h); L = $r.L; T = $r.T; R = $r.R; B = $r.B })
    }
    $true
}, [IntPtr]::Zero)

foreach ($w in $found) {
    "桌寵視窗：({0},{1})～({2},{3})  顯示中={4}" -f $w.L, $w.T, $w.R, $w.B, $w.Visible
    foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
        $a = $s.WorkingArea
        if ($w.L -lt $s.Bounds.Right -and $w.R -gt $s.Bounds.Left -and $w.T -lt $s.Bounds.Bottom -and $w.B -gt $s.Bounds.Top) {
            "所在螢幕：{0} 全螢幕 {1}  可用範圍 ({2},{3})～({4},{5})" -f $s.DeviceName, $s.Bounds, $a.Left, $a.Top, $a.Right, $a.Bottom
            if ($w.L -ge $a.Left -and $w.T -ge $a.Top -and $w.R -le $a.Right -and $w.B -le $a.Bottom) { "判定：整個在可用範圍內" }
            else { "判定：有部分超出可用範圍（可能壓在工作列上或螢幕外）" }
        }
    }
}
if ($found.Count -eq 0) { "找不到桌寵主視窗" }
