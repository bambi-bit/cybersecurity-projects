# Home Lab Network Segmentation with OPNsense

## Overview

This project demonstrates network segmentation using a firewall (OPNsense) placed between two isolated network segments in a VirtualBox home lab: an "attacker" segment (Kali Linux) and a "target" segment (Metasploitable2). Instead of both machines sitting on a flat, shared network where they can freely reach each other, OPNsense sits as the only bridge between them and enforces access with explicit firewall rules — the same core control pattern used in enterprise VLANs, DMZs, and zero-trust micro-segmentation.

**Goal:** Prove that (1) by default, nothing can cross between segments, and (2) once a specific rule is written, only that exact traffic is allowed through — everything else stays blocked.

## Topology

| Host | Segment | IP | VirtualBox Internal Network |
|---|---|---|---|
| Kali Linux (attacker) | WAN side | `10.0.1.50/24` | `intnet-attacker` |
| OPNsense (firewall) | Bridge | WAN: `10.0.1.1/24` · LAN: `10.0.2.1/24` | both |
| Metasploitable2 (target) | LAN side | `10.0.2.50/24` | `intnet-target` |

OPNsense's WAN interface faces Kali; its LAN interface faces Metasploitable2. No other path exists between the two segments — VirtualBox's "Internal Network" adapters create isolated virtual switches, so a VM only sees others explicitly attached to the same named network.

![OPNsense dashboard showing both interfaces up](screenshots/01-opnsense-dashboard.png)

## Step 1: Default-deny baseline

With OPNsense installed and both interfaces addressed, but before any custom rule existed, Kali could not reach Metasploitable2 at all:
