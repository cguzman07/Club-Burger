using System;
using System.Diagnostics;
using System.IO;

internal static class Lanzador
{
    static string BuscarPyw()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] candidatos =
        {
            Path.Combine(local, @"Programs\Python\Launcher\pyw.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"..\pyw.exe"),
            Path.Combine(local, @"Programs\Python\Python313\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python312\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python311\pythonw.exe"),
            Path.Combine(local, @"Programs\Python\Python310\pythonw.exe"),
            @"C:\Program Files\Python313\pythonw.exe",
            @"C:\Program Files\Python312\pythonw.exe",
            @"C:\Python313\pythonw.exe",
        };
        foreach (string ruta in candidatos)
        {
            try
            {
                if (File.Exists(ruta))
                    return Path.GetFullPath(ruta);
            }
            catch
            {
            }
        }
        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string dir in path.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
        {
            string pyw = Path.Combine(dir.Trim(), "pyw.exe");
            if (File.Exists(pyw))
                return pyw;
            string pythonw = Path.Combine(dir.Trim(), "pythonw.exe");
            if (File.Exists(pythonw) && pythonw.IndexOf("\\panel_dueno\\", StringComparison.OrdinalIgnoreCase) < 0)
                return pythonw;
        }
        return "pyw";
    }

    [STAThread]
    static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(root, "inicio_silencioso.py");
        if (!File.Exists(script))
            return;
        var psi = new ProcessStartInfo();
        psi.WorkingDirectory = root;
        psi.CreateNoWindow = true;
        psi.WindowStyle = ProcessWindowStyle.Hidden;
        string pyw = BuscarPyw();
        if (string.Equals(Path.GetFileName(pyw), "pyw.exe", StringComparison.OrdinalIgnoreCase) || pyw == "pyw")
        {
            psi.FileName = pyw;
            psi.Arguments = "-3 \"" + script + "\"";
        }
        else
        {
            psi.FileName = pyw;
            psi.Arguments = "\"" + script + "\"";
        }
        psi.UseShellExecute = !Path.IsPathRooted(psi.FileName);
        try
        {
            Process.Start(psi);
        }
        catch
        {
        }
    }
}
