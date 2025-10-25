

#include <windows.h>
#include <string>
#include <vector>
#include <iostream>
#include <shlwapi.h> 
#pragma comment(lib, "Shlwapi.lib")

static std::wstring quoteIfNeeded(const std::wstring &s) {
    if (s.find(L' ') != std::wstring::npos) {
        return L"\"" + s + L"\"";
    }
    return s;
}

std::wstring getExeFolder() {
    wchar_t buf[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, buf, MAX_PATH);
    std::wstring path(buf, buf + n);
    
    PathRemoveFileSpecW(buf);
    return std::wstring(buf);
}

int runProcessAndWait(const std::wstring &cmdLine, const std::wstring &workingDir = L"") {
    

    std::wstring fullCmd = L"cmd.exe /C " + cmdLine;

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    
    wchar_t *cmdWritable = _wcsdup(fullCmd.c_str()); 
    BOOL ok = CreateProcessW(
            NULL,
            cmdWritable,
            NULL,
            NULL,
            FALSE,
            0,
            NULL,
            workingDir.empty() ? NULL : workingDir.c_str(),
            &si,
            &pi
    );

    int exitCode = -1;
    if (!ok) {
        DWORD err = GetLastError();
        std::wcerr << L"CreateProcess failed. Error: " << err << L"\n";
        free(cmdWritable);
        return -1;
    }

    
    WaitForSingleObject(pi.hProcess, INFINITE);

    
    DWORD code = 0;
    if (GetExitCodeProcess(pi.hProcess, &code)) {
        exitCode = static_cast<int>(code);
    }

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    free(cmdWritable);
    return exitCode;
}

int wmain() {
    
    std::wstring baseFolder = getExeFolder();

    
    std::wstring pythonPath = L"python"; 

    
    std::vector<std::wstring> pyScripts = {
            L"script1.py",
            L"script2.py",
            L"scripts\\do_setup.py"   
    };

    
    std::wstring htmlFile = L"web\\index.html";

    
    for (const auto &rel : pyScripts) {
        std::wstring scriptPath = baseFolder + L"\\" + rel;
        std::wstring quotedScript = quoteIfNeeded(scriptPath);
        std::wstring quotedPython = quoteIfNeeded(pythonPath);

        std::wstring cmd = quotedPython + L" " + quotedScript;
        std::wcout << L"Running: " << cmd << L"\n";
        int rc = runProcessAndWait(cmd, baseFolder);
        if (rc != 0) {
            std::wcerr << L"Script exited with code " << rc << L". Aborting further scripts.\n";
            
            return rc;
        }
    }

    
    std::wstring htmlPath = baseFolder + L"\\" + htmlFile;
    std::wcout << L"Opening HTML: " << htmlPath << L"\n";

    
    HINSTANCE r = ShellExecuteW(NULL, L"open", htmlPath.c_str(), NULL, NULL, SW_SHOWNORMAL);
    if ((INT_PTR)r <= 32) {
        std::wcerr << L"Failed to open HTML. ShellExecute returned " << (INT_PTR)r << L"\n";
        return -1;
    }

    return 0;
}