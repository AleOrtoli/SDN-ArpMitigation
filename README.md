# Progetto SDN - Mininet, Ryu, QoS HTB e Sicurezza DAI

Progetto per il corso di **Network and Cloud Infrastructures** (A.A. 2025/2026, Prof. Giorgio Ventre).  
L'infrastruttura emula una rete industriale multi-subnet basata su OpenFlow 1.3 con due obiettivi primari:
1. **Quality of Service (QoS):** garanzia deterministica di banda per telemetria critica SCADA rispetto a traffico concorrente di bulk transfer su canale condiviso (bottleneck a 10 Mbps).
2. **Sicurezza sul Piano Dati:** rilevamento e mitigazione real-time di attacchi Man-in-the-Middle tramite **Dynamic ARP Inspection (DAI)** e isolamento hardware dell'attaccante.

---

## Struttura dei File

### Moduli Principali (Rete con QoS e DAI)
- `topo.py`: Definizione della topologia Mininet con router L3 Linux intermedio, switch Open vSwitch, configurazione delle code HTB su OVSDB (`s1-eth3`) e tuning del bufferbloat (`tc pfifo limit 10`).
- `controller.py`: Applicazione Ryu OpenFlow 1.3. Gestisce L2 Learning reattivo, classificazione proattiva dei flussi UDP su code HTB dedicate (priorità 50) e Dynamic ARP Inspection con blocco hardware dell'attaccante (priorità 100/1000).
- `test_script.py`: Script di test automatizzato headless per lo scenario di produzione (avvia server iperf3, genera traffico concorrente, esegue l'attacco ARP e raccoglie le metriche).
- `test_arp.py`: Script Python/Scapy per forgiare pacchetti gratuitous/reply ARP malevoli da `m1` impersonando il gateway `r1`.

### Moduli di Benchmark Speculari (Rete SENZA QoS)
- `controller_noqos.py`: Versione neutrale del controller Ryu. Mantiene intatte le logiche di L2 MAC learning e sicurezza DAI, ma omette l'assegnazione delle azioni `SetQueue` a priorità 50.
- `test_noqos.py`: Script di validazione comparativa. Ricostruisce a runtime una topologia speculare priva di configurazione di code HTB sul bottleneck, evidenziando il comportamento della rete non regolata sotto saturazione.

---

## Requisiti e Dipendenze Software

Il testbench è validato su ambiente Linux (**Ubuntu 20.04/22.04 LTS** o Mininet VM):

```bash
# Aggiornamento pacchetti di sistema
sudo apt update && sudo apt upgrade -y

# Componenti core, switch OVS e tool diagnostici
sudo apt install -y mininet openvswitch-switch openvswitch-testcontroller \
                    iperf3 iproute2 python3-pip python3-scapy

# Ryu SDN Framework e dipendenze compatibili
sudo pip3 install ryu eventlet==0.30.2

# Avvio del servizio Open vSwitch
sudo systemctl enable --now openvswitch-switch