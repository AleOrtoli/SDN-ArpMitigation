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
```


## Istruzioni per l'Esecuzione e la Riproducibilità

I test possono essere riprodotti in modalità completamente automatica (consigliata per i benchmark) oppure in modalità interattiva manuale tramite shell di Mininet.

---

### Metodo 1: Benchmark Automatizzato (Headless)

Questa modalità esegue la suite completa, genera il traffico, inietta l'attacco e salva i file diagnostici nella cartella results/.

#### Scenario A: Rete di Produzione (CON QoS HTB)
1. Terminale 1 (Controller SDN):
   ryu-manager controller.py

2. Terminale 2 (Testbench Automatizzato):
   sudo mn -c
   mkdir -p results
   sudo python3 test_script.py

3. Ispezione dei Risultati Generati:
   ls -la results/
   cat results/h2_iperf.txt          # Statistiche SCADA (loss 0.0%, jitter < 1.2 ms)
   cat results/h3_iperf.txt          # Statistiche bulk transfer (loss ~33%)
   cat results/arp_attack.txt        # Trigger dell'attacco ARP
   cat results/ping_after_attack.txt # Verifica 100% packet loss per l'attaccante
   cat results/ovs_queue_stats.txt   # Contatori hardware code HTB

#### Scenario B: Benchmark di Controllo (SENZA QoS)
1. Terminale 1 (Controller Neutro):
   ryu-manager controller_noqos.py

2. Terminale 2 (Testbench Speculare No-QoS):
   sudo mn -c
   sudo python3 test_noqos.py

---

### Metodo 2: Esecuzione Interattiva Manuale (Mininet CLI)

Per verificare puntualmente il funzionamento della rete tramite comandi diretti da prompt mininet>:

1. Avvio del Controller (Terminale 1):
   ryu-manager controller.py

2. Avvio della Topologia Mininet (Terminale 2):
   sudo mn -c
   sudo python3 topo.py

3. Verifica della Connettività L2/L3:
   mininet> pingall
   (Tutti i nodi devono comunicare correttamente tramite L2 learning e routing L3 di r1)

4. Validazione della QoS tramite iperf3:
   * Avviare i server riceventi nella LAN B:
     mininet> h2 iperf3 -s -p 5201 &
     mininet> h3 iperf3 -s -p 5202 &

   * Generare contemporaneamente i due flussi UDP dall'IPC h1:
     # Flusso Best-Effort saturante (12 Mbps verso h3)
     mininet> h1 iperf3 -c 10.0.2.2 -u -b 12M -p 5202 -t 15 &

     # Flusso Telemetria Prioritaria (2 Mbps verso h2)
     mininet> h1 iperf3 -c 10.0.2.1 -u -b 2M -p 5201 -t 15 &

   * Nel terminale del controller Ryu e nei report a video si noterà che h2 non subisce alcun packet loss, mentre h3 assorbe lo scarto dovuto alla saturazione del canale.

5. Validazione della Sicurezza (Dynamic ARP Inspection):
   * Lanciare l'attacco di ARP spoofing dall'host compromesso m1:
     mininet> m1 python3 test_arp.py

   * Sul Terminale 1 (Ryu) apparirà immediatamente:
     SECURITY ALERT: ARP Spoofing Detected! DPID: 1, Port: 2, Expected: 10.0.1.2/00:00:00:00:01:02, Got: 10.0.1.254/00:00:00:00:01:02

   * Verificare il blocco hardware dell'attaccante tentando di inviare traffico verso h1:
     mininet> m1 ping -c 3 10.0.1.1
     (Il test registra 100% packet loss, attestando l'isolamento hardware su s1)

---

## Procedura di Pulizia dell'Ambiente

In caso di arresto forzato dei processi o per azzerare lo stato delle interfacce virtuali prima di una nuova esecuzione:

sudo mn -c
sudo killall -9 ryu-manager iperf3 2>/dev/null