rule ReverseShell {
    meta:
        description = "Detects reverse shell patterns"
        score = 75
    strings:
        $s1 = "socket" nocase
        $s2 = "connect" nocase
        $s3 = "reverse" nocase
        $s4 = "nc " nocase
        $s5 = "netcat" nocase
    condition:
        2 of them
}

rule PowerShellAttack {
    meta:
        description = "PowerShell attack patterns"
        score = 60
    strings:
        $ps1 = "powershell" nocase
        $ps2 = "iex" nocase
        $ps3 = "invoke" nocase
        $ps4 = "downloadstring" nocase
    condition:
        $ps1 and ( $ps2 or $ps3 or $ps4 )
}

rule CmdExec {
    meta:
        description = "Command execution patterns"
        score = 50
    strings:
        $cmd1 = "cmd.exe" nocase
        $cmd2 = "system(" nocase
        $cmd3 = "subprocess" nocase
        $cmd4 = "exec(" nocase
    condition:
        any of them
}

rule Keylogger {
    meta:
        description = "Keylogger patterns"
        score = 80
    strings:
        $key1 = "keyboard" nocase
        $key2 = "keylogger" nocase
        $key3 = "hook" nocase
        $key4 = "keypress" nocase
    condition:
        2 of them
}
