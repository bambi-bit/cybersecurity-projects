# Metasploitable2 Vulnerability Assessment

**Assessor:** Mahnoor
**Target:** Metasploitable2 (10.0.2.20)
**Scanner host:** Kali Linux (10.0.2.10)
**Date:** September 2026

\---

## TLDR (plain language version)

I set up a small lab with two virtual machines: Kali Linux (the attacker/scanner box) and Metasploitable2 (a deliberately broken, outdated Linux box made for practicing on). I scanned Metasploitable2 with Nmap to find every open door (port) and what software was answering behind each one. Several of those doors are seriously broken on purpose: one lets anyone log in as an anonymous FTP guest and has a known backdoor, one hands out a root shell with zero login required, and one runs a chat server with a trojaned version that gives an attacker a shell too. I confirmed the worst of these with targeted scripts rather than just guessing from version numbers.

I also tried to run OpenVAS (a heavier, automated vulnerability scanner) for a second opinion, but getting it working ate most of the project's time: a firewall I had built in an earlier project was silently blocking traffic, the lab's virtual network kept forgetting its settings every time a VM restarted, and the scanner's own vulnerability database kept crashing during setup because the VM didn't have enough memory. Once I fixed the memory issue, OpenVAS's one-time database build still took most of a day, so I switched to Nmap's own vulnerability-scanning scripts to keep the project moving instead of losing another day waiting.

The bottom line: Metasploitable2 is about as insecure as a machine can be, which is the point of it, and this project is really a demonstration of two skills at once, finding vulnerabilities, and diagnosing and fixing a broken lab environment when nothing works on the first try.

\---

## Findings Cross-Referenced Against CVEs

Findings below are ordered by severity. "Confirmed" means detected by name/behavior via an active script, not just guessed from a version banner. "Version-based" means the finding relies on the service reporting an old version, which is treated as probable rather than certain.

|Port|Service / Version|Finding|CVE / Reference|Confidence|
|-|-|-|-|-|
|21|vsftpd 2.3.4|Known backdoor: a crafted username triggers a hidden shell on port 6200|CVE-2011-2523|Confirmed (Nmap `ftp-vsftpd-backdoor` behavior matches known signature; anonymous login also allowed)|
|1524|bindshell|Unauthenticated root shell listening directly on the port, no exploit needed|No CVE (intentional backdoor by design of the image)|Confirmed (Nmap service detection identifies it directly as "Metasploitable root shell")|
|6667 / 6697|UnrealIRCd|Trojaned server binary, connecting and sending a crafted string spawns a shell|CVE-2010-2075|Confirmed via `nmap --script irc-unrealircd-backdoor`, output: "Looks like trojaned version of unrealircd"|
|139 / 445|Samba 3.0.20|Username map script allows remote command execution; SMB signing disabled|CVE-2007-2447|Version-based (matches the known vulnerable Samba version range)|
|3632|distccd v1|Distributed compiler daemon accepts and runs arbitrary commands from any client|CVE-2004-2687|Version-based (default distccd config on this image is known-exploitable)|
|512 / 513 / 514|rexec, rlogin, rsh|Cleartext, trust-based remote login with no meaningful authentication|No single CVE (protocol-level weakness)|Confirmed (services identified directly by Nmap)|
|23|Telnet|Cleartext login credentials|No single CVE (protocol-level weakness)|Confirmed|
|25|Postfix (smtpd)|SSLv2 supported with export-grade ciphers; certificate expired in 2010|Related to CVE-2016-0800 (DROWN)|Version-based|
|22|OpenSSH 4.7p1|Old release; Debian-based builds of this era are linked to the predictable-key bug|CVE-2008-0166|Needs manual confirmation (key strength wasn't tested in this pass)|
|5900|VNC (protocol 3.3)|Password-only authentication, old protocol version, no encryption|No single CVE (weak-by-design)|Confirmed|
|8180 / 8009|Apache Tomcat 5.5 / AJP|End-of-life software; AJP connector is a known attack surface in this era|Related to CVE-2020-1938 (Ghostcat, later Tomcat AJP issue, included for context)|Version-based, needs manual check for default manager credentials|
|1099 / 53719|Java RMI / registry|Exposes remote method invocation, a common path to remote code execution|No single CVE (architecture-level exposure)|Confirmed exposed, exploitability not tested|
|8787|Ruby DRb|Distributed Ruby, arbitrary code execution is a known risk class for this service|No single CVE (architecture-level exposure)|Confirmed exposed, exploitability not tested|
|2049 / 111|NFS / rpcbind|Exposed RPC services, potential for unauthorized file share access|No single CVE (misconfiguration-level)|Confirmed exposed|
|3306|MySQL 5.0.51a|End-of-life database version, reachable directly over the network|No single CVE (EOL software)|Version-based|
|5432|PostgreSQL 8.3.0–8.3.7|End-of-life database version, reachable directly over the network|No single CVE (EOL software)|Version-based|
|80|Apache 2.2.8|Outdated web server, hosts the intentionally vulnerable web applications|No single CVE (EOL software)|Confirmed|
|6000|X11|Access denied on connection attempt|N/A|This is a control that held, noted as a positive finding|

**Notes on the port scan itself:**

* Nmap's OS fingerprint (Linux 2.6.x) was flagged by Nmap itself as unreliable, since the scan only covered the 30 already-known open ports rather than the full closed/open port mix OS fingerprinting normally needs.
* The SSL certificate on the mail service identifies the host as `ubuntu804-base`, confirming this is Ubuntu 8.04, consistent with the age of every service found.
* Four ports (36112, 37192, 47048, 53719) are dynamic RPC ports and will differ on a fresh boot; they are recorded here as observed at scan time, not as fixed configuration.

\---

## Full Write-Up

### 1\. Executive Summary

This assessment scanned Metasploitable2, an intentionally vulnerable Linux virtual machine, using Nmap for host and service discovery, followed by targeted vulnerability scripts. The host exposes 30 network services, several of which contain confirmed, actively exploitable backdoors requiring no authentication (vsftpd, the bindshell service, and UnrealIRCd). The overall risk profile is critical: multiple paths exist for an attacker to gain root-level access to the system without needing valid credentials of any kind. This is by design, Metasploitable2 exists specifically to demonstrate these classes of vulnerability, and the findings here reflect that intended state rather than an unexpected discovery.

### 2\. Scope and Methodology

**Scope:** Single host, Metasploitable2, at 10.0.2.20, on an isolated internal lab network shared with the Kali scanning host at 10.0.2.10. No production systems or external networks were in scope.

**Methodology:**

1. Host discovery and a full TCP port sweep (all 65,535 ports) with Nmap
2. Service and version detection, plus Nmap's default script set, against every open port found
3. Targeted vulnerability confirmation scripts against high-risk services (notably the UnrealIRCd backdoor check)
4. Nmap's vulnerability-scripting category (`--script vuln`) run against all open ports as the primary automated vulnerability detection layer
5. Manual cross-referencing of each identified service and version against public CVE records

**Tools used:**

* **Nmap** (v7.99): network discovery, port scanning, service/version fingerprinting, and scripted vulnerability checks
* **OpenVAS / Greenbone Vulnerability Management (GVM)** (v25.04): attempted as a secondary automated scanner (see Section 5.4, Obstacles)
* **VirtualBox**: hypervisor hosting both the Kali and Metasploitable2 virtual machines on an internal network

### 3\. Key Findings

See the full table in Step 4 above. The three most significant findings:

1. **vsftpd 2.3.4 backdoor (port 21):** a version of the FTP server that was distributed with a malicious backdoor slipped in by a third party in 2011. Anonymous login is also permitted.
2. **Unauthenticated root bindshell (port 1524):** connecting to this port directly hands over a root shell. No login, no exploit, no authentication of any kind.
3. **UnrealIRCd trojaned binary (ports 6667/6697):** confirmed via Nmap's dedicated detection script, which matched the known backdoor signature exactly.

!\[Nmap's irc-unrealircd-backdoor script confirming a trojaned UnrealIRCd binary](screenshots/unrealircd\_backdoor\_confirmed.png)
*Targeted detection script confirming the UnrealIRCd backdoor rather than relying on the version banner alone.*

### 4\. Obstacles Encountered and How They Were Resolved

This project involved as much lab troubleshooting as it did scanning. Documenting it here because the process is a real part of the work, and because it's a fair demonstration of network and Linux fundamentals under pressure.

!\[Nmap detecting vsftpd 2.3.4 and its anonymous login](screenshots/nmap\_vsftpd\_backdoor\_port21.png)
*Initial deep scan identifying vsftpd 2.3.4 and confirming anonymous FTP access.*

**1. GVM's Redis dependency wasn't running.**
On first setup, `gvm-check-setup` reported it could not reach Redis, and the OpenVAS scanner service hung indefinitely trying to start. Fixed by manually starting the dedicated Redis instance (`redis-server@openvas`) before restarting the rest of the stack.

**2. The lab network reset itself repeatedly.**
Every time either VM was powered off or the host machine went through a longer idle period, the manually assigned IP addresses on both Kali and Metasploitable2 disappeared, since they had been set with temporary, runtime-only commands rather than permanent configuration. This broke connectivity at the start of nearly every session and had to be diagnosed from scratch more than once. Eventually resolved by making both addresses permanent, `nmcli` on Kali and an edited `/etc/network/interfaces` file on Metasploitable2, so the lab no longer needs manual repair after a restart.

**3. A leftover firewall rule was silently blocking the scan.**
An earlier, separate project had built a segmented network using an OPNsense virtual firewall between Kali and Metasploitable2, with a rule that only allowed port 80 through. That rule was still active during this project and was rejecting every other port, which looked at first like a broken network rather than a firewall doing exactly what it had been configured to do. Diagnosed by testing raw TCP connections and comparing the resulting "connection refused" (an active reject) against Nmap's "filtered" result (a silent drop), which pointed at a firewall with an explicit reject rule rather than a dead link. Resolved by disabling the firewall's packet filtering (`pfctl -d`) for the duration of scanning. Because this setting doesn't survive a reboot, it needed to be reapplied more than once whenever the OPNsense VM restarted.

!\[Nmap identifying the unauthenticated root bindshell and distccd remote execution service](screenshots/nmap\_bindshell\_distccd.png)
*Deep scan output showing the bindshell on port 1524 and distccd on port 3632.*

**4. The GVM vulnerability feed was out of date.**
On first login to the OpenVAS web interface, the core vulnerability database (NVT) was 55 days out of date, and the supporting CVE and CVSS scoring feeds (SCAP, CERT) hadn't synced at all. Running a scan on stale data would have produced a report that missed nearly two months of known vulnerabilities. This had to be manually triggered and fully waited out before any scan could be trusted.

!\[OpenVAS reporting a 55-day-old vulnerability feed on first login](screenshots/openvas\_feed\_too\_old.png)
*Feed Status page showing the NVT feed 55 days out of date and other feeds mid-sync.*

**5. An interrupted sync left a stale lock file.**
A feed sync was manually stopped partway through, which left a lock file in place pointing to a process that no longer existed. Every later sync attempt hung indefinitely waiting for a lock that would never be released. Diagnosed with `lsof` to confirm nothing legitimate was holding it, then resolved by removing the stale lock file and re-running the sync to completion without interrupting it again.

**6. The scanner ran out of memory and kept crashing mid-import.**
Even after the feeds appeared current, the scan configuration templates (including the standard "Full and fast" profile) never actually loaded, and the task-creation screen showed no options. Checking the system logs revealed the real cause: the GVM database service was being killed by the operating system's out-of-memory protection every six to eight minutes, each time after its memory usage spiked to over 2 GB, because the Kali virtual machine had only been allocated 3.8 GB of RAM total. The service kept restarting and re-attempting the same large import from scratch, never surviving long enough to finish. This was resolved by increasing the virtual machine's allocated memory to 5.8 GB and giving it a second CPU core, after which the import no longer crashed.

!\[Diagnosing a hung GVM database process with strace, confirming zero system calls over five seconds](screenshots/gvmd\_hung\_process\_diagnosis.png)
*Using strace to confirm the database rebuild process had genuinely stalled rather than just running slowly.*

**7. The database rebuild still took most of a day, and later stalled outright.**
Even with enough memory, rebuilding GVM's entire CVE reference database from scratch (which covers every year back to 1999) took over eleven hours of continuous background processing. On a second attempt, after the whole stack was restarted for the memory upgrade, the same rebuild process stalled completely partway through, confirmed by attaching `strace` to the process and observing zero system calls over a five-second window, meaning it was not merely slow but genuinely frozen. Given the time already invested, the decision was made to stop troubleshooting OpenVAS further and use Nmap's own vulnerability-scripting engine as the primary scanning tool instead, which produced usable, confirmed results within minutes rather than requiring further hours of waiting.

!\[Vulnerability scripts running successfully once the network and firewall issues were resolved](screenshots/vulnscan\_finally\_running.png)
*Nmap's vulnerability script scan finally executing cleanly against all identified open ports.*

### 5\. Glossary of Tools and Terms Used

* **Nmap:** a network scanning tool used to find which devices are online, which ports are open on them, and what software is running behind those ports.
* **NSE (Nmap Scripting Engine):** a system built into Nmap that runs small, purpose-built scripts, including ones specifically designed to check for known vulnerabilities or backdoors.
* **OpenVAS / GVM (Greenbone Vulnerability Management):** a more heavyweight, automated vulnerability scanner that compares a target's services against a large, regularly updated database of known vulnerabilities.
* **CVE (Common Vulnerabilities and Exposures):** a public, standardized ID number given to a specific, documented security flaw, used so different tools and reports can refer to the same issue consistently.
* **CVSS (Common Vulnerability Scoring System):** a numeric severity score (0 to 10) assigned to a vulnerability, used to prioritize which issues matter most.
* **Backdoor:** a hidden or unintended way into a system that bypasses normal authentication, sometimes planted deliberately by an attacker who compromised the software's distribution.
* **Bindshell:** a program that opens a network port and hands over a command shell to whoever connects to it, with no login required.
* **Port:** a numbered network "door" a service listens on; scanning all 65,535 of them shows every potential entry point on a host.
* **Firewall (pf/pfSense/OPNsense):** software or a dedicated device that controls which network traffic is allowed to pass, based on configured rules.
* **NVT (Network Vulnerability Test):** OpenVAS's own internal library of vulnerability-checking scripts, separate from the public CVE/CVSS reference data.
* **SCAP (Security Content Automation Protocol):** the standardized feed of CVE and CVSS reference data that OpenVAS uses to enrich its findings with official severity scores.
* **OOM killer (Out-Of-Memory killer):** a Linux kernel feature that forcibly terminates a process when the system has run out of available memory, to keep the whole machine from crashing.
* **strace:** a diagnostic tool that shows every low-level system call a running program makes, used here to prove a stuck process was truly frozen rather than just slow.
* **ARP (Address Resolution Protocol):** the process by which one device on a local network finds another device's hardware (MAC) address, used here to confirm two VMs could actually see each other at the most basic network level.

### 6\. Recommendations

Standard for this kind of intentionally vulnerable host, recommendations focus on what a real-world equivalent should do rather than "fixing" Metasploitable2 itself:

* Never run vsftpd 2.3.4 or any similarly aged, unpatched service on a production or internet-facing system
* Disable or remove any bindshell, rexec, rlogin, or rsh service entirely; these have no place on a modern network
* Replace end-of-life software (Apache 2.2.8, MySQL 5.0, PostgreSQL 8.3, Tomcat 5.5) with supported, patched versions
* Enforce SMB signing and disable SSLv2/export-grade ciphers wherever legacy protocol support is found
* Restrict or firewall off administrative and RPC-style services (Java RMI, Ruby DRb, NFS, rpcbind) from any untrusted network segment

\---

*Raw scan output, screenshots, and the Nmap `.nmap`/`.xml`/`.gnmap` files referenced above are included alongside this report in the project repository.*

