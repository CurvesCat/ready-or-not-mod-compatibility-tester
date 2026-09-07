using System.Runtime.InteropServices;

namespace RoNCT.App.Services;

/// <summary>
/// Win32 IFileOpenDialog helpers so folder/file pickers can open at a real
/// start directory instead of the generic Documents location used by the
/// Windows.Storage.Pickers projection.
/// </summary>
internal static class NativeFileDialog
{
    private const uint S_OK = 0;
    private const uint FOS_FORCEFILESYSTEM = 0x00000040;
    private const uint FOS_ALLOWMULTISELECT = 0x00000200;
    private const uint FOS_FILEMUSTEXIST = 0x00001000;
    private const uint FOS_PATHMUSTEXIST = 0x00000800;
    private const uint FOS_PICKFOLDERS = 0x00000020;
    private const uint SIGDN_FILESYSPATH = 0x80058000;

    public static string? PickFolder(IntPtr owner, string? initialDirectory)
    {
        var dialog = (IFileDialog)(object)new FileOpenDialogRCW();
        try
        {
            dialog.GetOptions(out var current);
            dialog.SetOptions(current | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
            ApplyStartFolder(dialog, initialDirectory);

            if (dialog.Show(owner) != S_OK)
            {
                return null;
            }

            if (dialog.GetResult(out var shellItem) != S_OK || shellItem is null)
            {
                return null;
            }

            try
            {
                return GetPath(shellItem);
            }
            finally
            {
                Marshal.FinalReleaseComObject(shellItem);
            }
        }
        finally
        {
            Marshal.FinalReleaseComObject(dialog);
        }
    }

    public static string? PickFile(
        IntPtr owner,
        string? initialDirectory,
        IReadOnlyList<string> extensions)
    {
        var dialog = (IFileDialog)(object)new FileOpenDialogRCW();
        try
        {
            dialog.GetOptions(out var current);
            var options = current | FOS_FORCEFILESYSTEM
                | FOS_FILEMUSTEXIST
                | FOS_PATHMUSTEXIST;
            dialog.SetOptions(options);

            var specs = extensions
                .Where(ext => !string.IsNullOrWhiteSpace(ext))
                .Select(ext => new COMDLG_FILTERSPEC
                {
                    pszName = $"{ext.TrimStart('.')} files ({ext})",
                    pszSpec = ext,
                })
                .Append(new COMDLG_FILTERSPEC
                {
                    pszName = "All files (*.*)",
                    pszSpec = "*.*",
                })
                .ToArray();
            dialog.SetFileTypes((uint)specs.Length, specs);
            dialog.SetFileTypeIndex(1);

            ApplyStartFolder(dialog, initialDirectory);

            if (dialog.Show(owner) != S_OK)
            {
                return null;
            }

            if (dialog.GetResult(out var shellItem) != S_OK || shellItem is null)
            {
                return null;
            }

            try
            {
                return GetPath(shellItem);
            }
            finally
            {
                Marshal.FinalReleaseComObject(shellItem);
            }
        }
        finally
        {
            Marshal.FinalReleaseComObject(dialog);
        }
    }

    public static IReadOnlyList<string> PickPakFiles(IntPtr owner, string? initialDirectory)
    {
        var dialog = (IFileOpenDialog)(object)new FileOpenDialogRCW();
        try
        {
            dialog.GetOptions(out var options);
            options |= FOS_FORCEFILESYSTEM
                | FOS_FILEMUSTEXIST
                | FOS_PATHMUSTEXIST
                | FOS_ALLOWMULTISELECT;
            dialog.SetOptions(options);

            var filters = new[]
            {
                new COMDLG_FILTERSPEC
                {
                    pszName = "Ready or Not mods (*.pak)",
                    pszSpec = "*.pak",
                },
                new COMDLG_FILTERSPEC
                {
                    pszName = "All files (*.*)",
                    pszSpec = "*.*",
                },
            };
            dialog.SetFileTypes((uint)filters.Length, filters);
            dialog.SetFileTypeIndex(1);

            ApplyStartFolder(dialog, initialDirectory);

            if (dialog.Show(owner) != S_OK)
            {
                return Array.Empty<string>();
            }

            if (dialog.GetResults(out var results) != S_OK || results is null)
            {
                return Array.Empty<string>();
            }

            try
            {
                results.GetCount(out var count);
                var selected = new List<string>(checked((int)count));
                for (uint index = 0; index < count; index++)
                {
                    if (results.GetItemAt(index, out var item) != S_OK || item is null)
                    {
                        continue;
                    }

                    try
                    {
                        var path = GetPath(item);
                        if (!string.IsNullOrEmpty(path))
                        {
                            selected.Add(path);
                        }
                    }
                    finally
                    {
                        Marshal.FinalReleaseComObject(item);
                    }
                }
                return selected;
            }
            finally
            {
                Marshal.FinalReleaseComObject(results);
            }
        }
        finally
        {
            Marshal.FinalReleaseComObject(dialog);
        }
    }

    private static void ApplyStartFolder(IFileDialog dialog, string? directory)
    {
        if (string.IsNullOrWhiteSpace(directory) || !Directory.Exists(directory))
        {
            return;
        }
        var riid = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"); // IShellItem
        if (SHCreateItemFromParsingName(directory, IntPtr.Zero, ref riid, out var item) == S_OK)
        {
            try
            {
                dialog.SetFolder(item);
            }
            finally
            {
                Marshal.ReleaseComObject(item);
            }
        }
    }

    private static string? GetPath(IShellItem item)
    {
        if (item.GetDisplayName(SIGDN_FILESYSPATH, out var pointer) != S_OK || pointer == IntPtr.Zero)
        {
            return null;
        }
        try
        {
            return Marshal.PtrToStringUni(pointer);
        }
        finally
        {
            Marshal.FreeCoTaskMem(pointer);
        }
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int SHCreateItemFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string path,
        IntPtr bindContext,
        ref Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IShellItem item);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct COMDLG_FILTERSPEC
    {
        [MarshalAs(UnmanagedType.LPWStr)]
        public string pszName;

        [MarshalAs(UnmanagedType.LPWStr)]
        public string pszSpec;
    }

    [ComImport, ClassInterface(ClassInterfaceType.None), Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    private class FileOpenDialogRCW
    {
    }

    [ComImport, Guid("42F85136-DB7E-439C-85F1-E4075D135FC8"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IFileDialog
    {
        [PreserveSig]
        uint Show(IntPtr owner);

        [PreserveSig]
        uint SetFileTypes(
            [In] uint count,
            [In, MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 0)] COMDLG_FILTERSPEC[] filters);

        [PreserveSig]
        uint SetFileTypeIndex([In] uint index);

        [PreserveSig]
        uint GetFileTypeIndex(out uint index);

        [PreserveSig]
        uint Advise(IntPtr events, out uint cookie);

        [PreserveSig]
        uint Unadvise(uint cookie);

        [PreserveSig]
        uint SetOptions([In] uint options);

        [PreserveSig]
        uint GetOptions(out uint options);

        [PreserveSig]
        uint SetDefaultFolder([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder);

        [PreserveSig]
        uint SetFolder([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder);

        [PreserveSig]
        uint GetFolder([MarshalAs(UnmanagedType.Interface)] out IShellItem folder);

        [PreserveSig]
        uint GetCurrentSelection([MarshalAs(UnmanagedType.Interface)] out IShellItem selection);

        [PreserveSig]
        uint SetFileName([In, MarshalAs(UnmanagedType.LPWStr)] string name);

        [PreserveSig]
        uint GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string name);

        [PreserveSig]
        uint SetTitle([In, MarshalAs(UnmanagedType.LPWStr)] string title);

        [PreserveSig]
        uint SetOkButtonLabel([In, MarshalAs(UnmanagedType.LPWStr)] string text);

        [PreserveSig]
        uint SetFileNameLabel([In, MarshalAs(UnmanagedType.LPWStr)] string label);

        [PreserveSig]
        uint GetResult([MarshalAs(UnmanagedType.Interface)] out IShellItem result);

        [PreserveSig]
        uint AddPlace([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder, uint placement);

        [PreserveSig]
        uint SetDefaultExtension([In, MarshalAs(UnmanagedType.LPWStr)] string extension);

        [PreserveSig]
        uint Close(uint hr);

        [PreserveSig]
        uint SetClientGuid(ref Guid guid);

        [PreserveSig]
        uint ClearClientData();

        [PreserveSig]
        uint SetFilter(IntPtr filter);
    }

    [ComImport, Guid("D57C7288-D4AD-4768-BE02-9D969532D960"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IFileOpenDialog : IFileDialog
    {
        [PreserveSig]
        new uint Show(IntPtr owner);

        [PreserveSig]
        new uint SetFileTypes(
            [In] uint count,
            [In, MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 0)] COMDLG_FILTERSPEC[] filters);

        [PreserveSig]
        new uint SetFileTypeIndex([In] uint index);

        [PreserveSig]
        new uint GetFileTypeIndex(out uint index);

        [PreserveSig]
        new uint Advise(IntPtr events, out uint cookie);

        [PreserveSig]
        new uint Unadvise(uint cookie);

        [PreserveSig]
        new uint SetOptions([In] uint options);

        [PreserveSig]
        new uint GetOptions(out uint options);

        [PreserveSig]
        new uint SetDefaultFolder([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder);

        [PreserveSig]
        new uint SetFolder([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder);

        [PreserveSig]
        new uint GetFolder([MarshalAs(UnmanagedType.Interface)] out IShellItem folder);

        [PreserveSig]
        new uint GetCurrentSelection([MarshalAs(UnmanagedType.Interface)] out IShellItem selection);

        [PreserveSig]
        new uint SetFileName([In, MarshalAs(UnmanagedType.LPWStr)] string name);

        [PreserveSig]
        new uint GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string name);

        [PreserveSig]
        new uint SetTitle([In, MarshalAs(UnmanagedType.LPWStr)] string title);

        [PreserveSig]
        new uint SetOkButtonLabel([In, MarshalAs(UnmanagedType.LPWStr)] string text);

        [PreserveSig]
        new uint SetFileNameLabel([In, MarshalAs(UnmanagedType.LPWStr)] string label);

        [PreserveSig]
        new uint GetResult([MarshalAs(UnmanagedType.Interface)] out IShellItem result);

        [PreserveSig]
        new uint AddPlace([In, MarshalAs(UnmanagedType.Interface)] IShellItem folder, uint placement);

        [PreserveSig]
        new uint SetDefaultExtension([In, MarshalAs(UnmanagedType.LPWStr)] string extension);

        [PreserveSig]
        new uint Close(uint hr);

        [PreserveSig]
        new uint SetClientGuid(ref Guid guid);

        [PreserveSig]
        new uint ClearClientData();

        [PreserveSig]
        new uint SetFilter(IntPtr filter);

        [PreserveSig]
        uint GetResults([MarshalAs(UnmanagedType.Interface)] out IShellItemArray results);

        [PreserveSig]
        uint GetSelectedItems([MarshalAs(UnmanagedType.Interface)] out IShellItemArray items);
    }

    [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellItem
    {
        [PreserveSig]
        uint BindToHandler(IntPtr bindContext, ref Guid handlerId, ref Guid riid, out IntPtr result);

        [PreserveSig]
        uint GetParent([MarshalAs(UnmanagedType.Interface)] out IShellItem parent);

        [PreserveSig]
        uint GetDisplayName([In] uint nameType, out IntPtr name);

        [PreserveSig]
        uint GetAttributes([In] uint mask, out uint attributes);

        [PreserveSig]
        uint Compare(
            [In, MarshalAs(UnmanagedType.Interface)] IShellItem other,
            [In] uint hint,
            out int order);
    }

    [ComImport, Guid("B63EA76D-1F85-456F-A19C-48159EFA858B"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellItemArray
    {
        [PreserveSig]
        uint BindToHandler(IntPtr bindContext, ref Guid handlerId, ref Guid riid, out IntPtr result);

        [PreserveSig]
        uint GetPropertyStore(uint flags, ref Guid riid, out IntPtr store);

        [PreserveSig]
        uint GetPropertyDescriptionList(ref long key, ref Guid riid, out IntPtr list);

        [PreserveSig]
        uint GetAttributes(uint flags, uint mask, out uint attributes);

        [PreserveSig]
        uint GetCount(out uint count);

        [PreserveSig]
        uint GetItemAt([In] uint index, [MarshalAs(UnmanagedType.Interface)] out IShellItem item);

        [PreserveSig]
        uint EnumItems(IntPtr enumerator);
    }
}
