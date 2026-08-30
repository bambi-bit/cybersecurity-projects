# Cybersecurity Projects
A collection of hands-on cybersecurity projects, built and tested in an isolated
home lab environment (Kali Linux + Metasploitable2, VirtualBox).
## Projects
### [SSH Log Monitoring Agent](./log-monitor-agent)
A Python agent that tails authentication logs in real time and flags suspicious
activity — brute-force attempts, username enumeration, and privilege escalation —
using rule-based threshold analysis. Tested against live simulated attack traffic.

### [Home Lab Network Segmentation](./network-segmentation)
An OPNsense firewall placed between two isolated network segments (Kali as
"attacker," Metasploitable2 as "target") to enforce least-privilege access
between them. Proves default-deny blocks all inter-segment traffic, then
validates a single explicit allow-rule (TCP/80 only) passes exactly that
traffic while everything else stays blocked — the same control pattern
behind enterprise VLANs, DMZs, and zero-trust micro-segmentation.
## About
Built while working toward a cybersecurity specialization (Network and
Infrastructure Security), with a home lab used for hands-on practice alongside
coursework and TryHackMe learning paths.
